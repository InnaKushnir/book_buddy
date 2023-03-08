from django.shortcuts import render, get_object_or_404
from flask import Flask, redirect
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
import requests
import json
from library.models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer,
    BorrowingListSerializer,
    BorrowingUpdateSerializer,
    BorrowingCreateSerializer,
    PaymentSerializer,
)
from rest_framework import status, generics, viewsets, mixins
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



def create_session(amount, name):
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
        success_url="http://127.0.0.1:8000/api/library/payments/",
        cancel_url="http://127.0.0.1:8000/api/library/borrowings/",
    )
    # Return the session ID
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
            session= create_session(money, book.title)

            request.session['session_id'] = session.id
            request.session['session_url'] = session.url
            SESSION_URL = session.url


            instance = self.get_object()
            request.session['borrowing_pk'] = instance.pk


            response = redirect(SESSION_URL)

            print(session.id, session.url, borrowing.pk)
            print((response.get_data(), response.status_code, response.content_type))

            return HttpResponse(response.get_data(), status=response.status_code, content_type=response.content_type)
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
                + (actual_return_date - borrowing.expected_return_date).days * settings.FINE_MULTIPLIER
            ) * book.daily_fee
        else:
            money = 5 * book.daily_fee

        return money


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset

        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
            borrowing_id = self.request.query_params.get("borrowing_id")
            if borrowing_id is not None:
                queryset = queryset.filter(borrowing_id=borrowing_id)
            print(borrowing_id)

        return queryset
    def create(self, request, *args, **kwargs):

        session_id = request.session.get('session_id')
        session_url = request.session.get('session_url')
        borrowing_pk = request.session.get('borrowing_pk')

        print(session_id, session_url, borrowing_pk)
        print(request.session.items())

        # Retrieve the Stripe session object using the session ID
        session = stripe.checkout.Session.retrieve(session_id)

        session.payment_status = "paid"

        borrowing = get_object_or_404(Borrowing, pk=borrowing_pk)

        if session.payment_status == 'paid':
            # Payment was successful, create a Payment object in your database
            payment = Payment.objects.create(
                money_to_pay=3.0 ,# session.amount_total,
                borrowing=borrowing,
                status="PAID",
                type="PAYMENT",

                session_id=session_id,
                session_url=session_url,
            )

            # Return a success response
            print("success")
            payment.save()
            print(payment)

            return Response({'status': 'success'})

        else:
            # Payment was not successful, return an error response
            print("error")
            return Response({'status': 'error'})

def payment_success(request):
    return render(request, "payment_success.html")


