import os
import requests
import json
import stripe
import datetime

from django.urls import reverse
from django.shortcuts import render, get_object_or_404
from flask import Flask, redirect
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin
from django.db import transaction
from django.conf import settings
from django.http import HttpRequest
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from drf_spectacular.utils import extend_schema, OpenApiParameter

from library.notifications import new_borrowing
from library.models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer,
    BorrowingListSerializer,
    BorrowingUpdateSerializer,
    BorrowingCreateSerializer,
    PaymentSerializer,
)
from library.stripe import order_success


stripe.api_key = settings.STRIPE_SECRET_KEY


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (AllowAny,)

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminUser()]
        return super().get_permissions()


def create_session(request, amount, name):
    # Convert the amount from dollars to cents
    amount_cents = int(amount * 100)
    url = reverse("library:payment-success")
    success_url = (request.build_absolute_uri(url)[:-1] + "?session_id={CHECKOUT_SESSION_ID}")
    cancel_url = request.build_absolute_uri(reverse("library:payment-cancel"))

    # Create a new session in Stripe
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": name,
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url)

    return session


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all().select_related("book")
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "update":
            return BorrowingUpdateSerializer
        elif self.action == "create":
            return BorrowingCreateSerializer
        return BorrowingListSerializer

    def get_queryset(self):
        queryset = self.queryset.select_related("book")

        is_active_ = self.request.query_params.get("is_active")
        user_id = self.request.query_params.get("user")
        overdue = self.request.query_params.get("overdue")

        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        if is_active_ is not None:
            if is_active_.lower()=="false":
                queryset = queryset.filter(
                    is_active=False)
            elif is_active_.lower()=="true":
                queryset = queryset.filter(
                    is_active=True)
        if overdue is not None:
            if overdue.lower()=="false":
                queryset = queryset.filter(actual_return_date__isnull=False)
            if overdue.lower()=="true":
                queryset = queryset.filter(
                expected_return_date__lt=datetime.date.today()
                ).filter(actual_return_date=None)

        return queryset
    """ Create Payment session, change Borrowing object, create Payment object """
    @transaction.atomic
    def update(self, request, pk=None):
        borrowing = Borrowing.objects.get(pk=pk)

        if borrowing.actual_return_date is None:
            borrowing.actual_return_date = datetime.date.today()
            borrowing.is_active = False
            book = borrowing.book
            book.inventory += 1

            serializer = BorrowingUpdateSerializer(
                borrowing,
                many=False,
                partial=True,
                data={"actual_return_date": datetime.date.today()},
            )

            serializer.is_valid()
            borrowing.save()
            book.save()
            money = self.pay_money()
            session = create_session(request, money, book.title)

            request.session["session_id"] = session.id
            request.session["session_url"] = session.url
            SESSION_URL = session.url

            payment = Payment.objects.create(
                money_to_pay=money,
                borrowing=borrowing,
                status="PAID",
                type="PAYMENT",
                session_id=session.id,
                session_url=session.url,
            )
            payment.save()

            instance = self.get_object()
            request.session["borrowing_pk"] = instance.pk
            request.session["payment_pk"] = payment.pk

            response = redirect(SESSION_URL)


            return HttpResponse(response.get_data(),
                                content_type=response.content_type)
        else:
            serializer = BorrowingUpdateSerializer(borrowing)
        return Response(serializer.data)

    def perform_create(self, serializer, **kwargs):
        serializer.save(user=self.request.user)

        id = self.request.data["book"]
        book = get_object_or_404(Book, pk=id)
        expected_return_date = self.request.data["expected_return_date"]

        new_borrowing(self.request.user.id, id, book, expected_return_date)

        self.change_inventory_create()

    def change_inventory_create(self):
        book_id = self.request.data["book"]
        book = get_object_or_404(Book, pk=book_id)
        book.inventory -= 1
        book.save()

    """Calculate money to pay for borrowing"""
    def pay_money(self):
        borrowing = self.get_object()
        book = borrowing.book
        actual_return_date = datetime.date.today()
        number_of_days = (
                borrowing.expected_return_date - borrowing.borrow_date).days
        if borrowing.expected_return_date < actual_return_date:
            money = (
                number_of_days
                + (actual_return_date - borrowing.expected_return_date).days
                * settings.FINE_MULTIPLIER
            ) * book.daily_fee
        else:
            money = number_of_days * book.daily_fee

        return money

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="user",
                type={"type": "int"},
                description="Permissions only for admin, add parameter 'is_active'"
                            ", (ex. ?user=1&is_active=True  return all current borrowings of user with id=1,"
                            "?user=2is_active=False   return all returned borrowings of user id=2)",
                required=False,

            ),
            OpenApiParameter(
                name="is_active",
                type={"type": "Boolean"},
                description="Permissions only for admin, add parameter 'user'"
                            ", (ex. ?user=1&is_active=True  return all current borrowings of user with id=1,"
                            "?user=2is_active=False   return all returned borrowings of user id=2)",
                required=False,

            ),
            OpenApiParameter(
                name="overdue",
                type={"type": "string"},
                description="(ex. ?overdue   return all overdue borrowings for current user, "
                            "or all overdue borrowings, if current user is admin)",
                required=False,

            ),
        ],
    )

    def list(self, request, *args, **kwargs):
        return super(BorrowingViewSet, self).list(request, *args, **kwargs)


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)
    queryset = Payment.objects.all().select_related("borrowing")

    def get_queryset(self):
        queryset = Payment.objects.all().select_related("borrowing")
        user = self.request.user

        if not self.request.user.is_staff:
            queryset = queryset.filter(
                borrowing__user=user).select_related("borrowing")

        return queryset


    """Endpoint, if payment success"""
    @action(
        detail=False,
        methods=["GET"],
        url_path="success",
        permission_classes=[IsAuthenticated],
    )
    def success(self, request) -> Response:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session_id = request.GET.get("session_id")
        payment = Payment.objects.get(session_id=session_id)
        payment.status = "PAID"
        payment.save()

        return Response(data=f"Your payment is successful", status=status.HTTP_200_OK)

    """Endpoint, if payment cancel"""
    @action(
        detail=False,
        methods=["GET"],
        url_path="cancel",
        permission_classes=[IsAuthenticated],
    )
    def cancel(self, request) -> Response:
        return Response(
            data="Try to pay later within 24 hours session is available",
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )
