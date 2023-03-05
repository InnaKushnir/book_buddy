from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django.http import JsonResponse
import requests
import json
from library.models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer,
    BorrowingListSerializer,
    BorrowingUpdateSerializer,
    BorrowingCreateSerializer,
    PaymentListSerializer,
)
from rest_framework.views import APIView
from library.stripe import checkout_session
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from library.notifications import new_borrowing

import datetime
from django.db import transaction
import stripe
from django.conf import settings
import os

stripe.api_key = settings.STRIPE_SECRET_KEY


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (AllowAny,)

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminUser()]
        return super().get_permissions()


class CreateSessionView(APIView):
    def create_session(self, amount, name):
        # Convert the amount from dollars to cents
        amount_cents = int(amount * 100)

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
            success_url="https://127.0.0.1:800/library/borrowings/",
            cancel_url="https://127.0.0.1:800/library/borrowings/l",
        )
        # Return the session ID
        return session.id, session.url


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
        user_id = self.request.query_params.get("user_id")
        overdue = self.request.query_params.get("overdue")

        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        if (
            (is_active_ is not None)
            and (user_id is not None)
            and self.request.user.is_staff
        ):
            if str(is_active_) == "False":
                queryset = queryset.filter(is_active=False).filter(user_id=user_id)
            else:
                queryset = queryset.filter(is_active=True).filter(user_id=user_id)
        if overdue:
            queryset = queryset.filter(
                expected_return_date__lt=datetime.date.today()
            ).filter(actual_return_date=None)

        return queryset

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
            session_id = CreateSessionView().create_session(money, book.title)
            print(session_id)
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

    def pay_money(self):
        borrowing = self.get_object()
        book = borrowing.book
        actual_return_date = datetime.date.today()
        number_of_days = (borrowing.expected_return_date - borrowing.borrow_date).days
        if borrowing.expected_return_date < actual_return_date:
            money = (
                number_of_days
                + (actual_return_date - borrowing.expected_return_date).days * 2
            ) * book.daily_fee
        else:
            money = (
                borrowing.actual_return_date - borrowing.borrow_date
            ).days * book.daily_fee

        return money


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related("borrowing_id")
    serializer_class = PaymentListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset.select_related("borrowing_id")

        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
