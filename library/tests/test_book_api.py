import datetime
import json
import os
from unittest import mock
from unittest.mock import patch
from datetime import date
from datetime import timedelta

import stripe
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse
from library.models import Book, Borrowing, Payment
from library.notifications import new_borrowing, overdue_borrowing
from library.tasks import run_sync_with_api
from library.serializers import (
    BookSerializer,
    BorrowingListSerializer,
    PaymentSerializer,
)
from rest_framework import status
from rest_framework.test import APIClient

stripe.api_key = os.getenv("STRIPE_TEST_SECRET")
BORROWING_URL = reverse("library:borrowing-list")
BOOK_URL = reverse("library:book-list")
PAYMENT_URL = reverse("library:payment-success")
BOT_NUMBER = 417193906


def detail_url(model, object_id):
    return reverse(f"library:{model._meta.model_name}-detail", args=[object_id])


def sample_book(**kwargs):
    defaults = {
        "author": "Jerome K. Jerome",
        "title": "Three men in a boat",
        "cover": "SOFT",
        "daily_fee": 0.15,
        "inventory": 20,
    }
    defaults.update(kwargs)
    return Book.objects.create(**defaults)


def sample_borrowing(**kwargs):
    defaults = {
        "borrow_date": datetime.date.today(),
        "expected_return_date": "2023-04-30",
        "actual_return_date": None,
        "is_active": True,
        "book": sample_book(),
        "user": self.user,
    }
    defaults.update(kwargs)
    return Borrowing.objects.create(**defaults)


class UnauthenticatedBookAPITests(TestCase):
    def SetUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(BORROWING_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_not_required(self):
        sample_book()
        res = self.client.get(BOOK_URL)
        books = Book.objects.all()
        serializer = BookSerializer(books, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)


class AuthenticateBorrowingTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="12345@test.com", password="12345test"
        )
        self.client.force_authenticate(self.user)

        self.defaults = {
            "borrow_date": "2023-05-28",
            "expected_return_date": "2023-06-30",
            "actual_return_date": None,
            "is_active": True,
            "book": sample_book(),
            "user": self.user,
        }

    def tearDown(self):
        del self.user
        del self.defaults

    def test_list_borrowing(self):
        res = self.client.get(BORROWING_URL)
        borrowings = Borrowing.objects.all()
        serializer = BorrowingListSerializer(borrowings, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_create_borrowing_and_inventory_reduce(self):
        book = Book.objects.create(
            author="Jerome K. Jerome",
            title="Three men in a boat",
            cover="SOFT",
            daily_fee=0.15,
            inventory=20,
        )

        payload = {
            "borrow_date": datetime.date.today(),
            "expected_return_date": "2023-10-28",
            "actual_return_date": "",
            "is_active": True,
            "book": book.id,
            "user": self.user.id,
        }
        res = self.client.post(BORROWING_URL, payload)
        borrowing = Borrowing.objects.last()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            if key not in ["actual_return_date", "book", "user"]:
                self.assertEqual(str(payload[key]), str(getattr(borrowing, key)))
            elif key == "actual_return_date":
                self.assertEqual("None", str(getattr(borrowing, key)))
            elif key == "book":
                self.assertEqual(borrowing.book.title, book.title)
                self.assertEqual(borrowing.book.author, book.author)
                self.assertEqual(float(borrowing.book.daily_fee), book.daily_fee)
                self.assertEqual(borrowing.book.cover, book.cover)
                self.assertEqual(borrowing.book.inventory, book.inventory - 1)
            elif key == "user":
                self.assertEqual(borrowing.user.email, self.user.email)
                self.assertEqual(borrowing.user.password, self.user.password)

    def test_filter_borrowings_by_overdue(self):
        borrowing1 = Borrowing.objects.create(**self.defaults)
        borrowing1.borrow_date = "2023-05-20"
        borrowing1.expected_return_date = "2023-05-28"
        borrowing1.save()
        borrowing2 = Borrowing.objects.create(**self.defaults)
        borrowing2.borrow_date = "2023-05-15"
        borrowing2.expected_return_date = "2023-05-27"
        borrowing2.save()
        borrowing3 = Borrowing.objects.create(**self.defaults)
        borrowing3.borrow_date = "2023-07-2"
        borrowing3.expected_return_date = "2024-12-30"
        borrowing3.save()

        res = self.client.get(BORROWING_URL, {"overdue": "True"})

        serializer1 = BorrowingListSerializer(borrowing1)
        serializer2 = BorrowingListSerializer(borrowing2)
        serializer3 = BorrowingListSerializer(borrowing3)

        self.assertIn(json.dumps(serializer1.data), json.dumps(res.data))
        self.assertIn(json.dumps(serializer2.data), json.dumps(res.data))
        self.assertNotIn(json.dumps(serializer3.data), json.dumps(res.data))

    def test_retrieve_borrowing_detail(self):
        borrowing = Borrowing.objects.create(**self.defaults)
        url = detail_url(borrowing.__class__, borrowing.id)
        res = self.client.get(url)

        serializer = BorrowingListSerializer(borrowing)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_book_detail(self):
        book = sample_book()
        url = detail_url(book.__class__, book.id)
        res = self.client.get(url)

        serializer = BookSerializer(book)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_book_forbidden(self):
        payload = {
            "author": "Jerome K. Jerome",
            "title": "Three men in a boat",
            "cover": "SOFT",
            "daily_fee": 0.15,
            "inventory": 20,
        }
        res = self.client.post(BOOK_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBorrowingTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="12345@test.com", password="12345test", is_staff=True
        )
        self.client.force_authenticate(self.user)

        self.defaults = {
            "borrow_date": "2023-04-28",
            "expected_return_date": "2023-05-28",
            "actual_return_date": None,
            "is_active": True,
            "book": sample_book(),
            "user": self.user,
        }
        self.borrowing = Borrowing.objects.create(**self.defaults)

        def tearDown(self):
            del self.user
            del self.defaults

    def test_create_book(self):
        payload = {
            "author": "Jerome K. Jerome",
            "title": "Three men in a boat",
            "cover": "SOFT",
            "daily_fee": 0.24,
            "inventory": 20,
        }
        res = self.client.post(BOOK_URL, payload)
        book = Book.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            if key == "daily_fee":
                self.assertEqual(float(payload[key]), float(getattr(book, key)))
            else:
                self.assertEqual(payload[key], getattr(book, key))

    def test_delete_book(self):
        book = sample_book()
        url = detail_url(book.__class__, book.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(id=book.id).exists())

    def test_delete_borrowing(self):
        borrowing = self.borrowing
        url = detail_url(borrowing.__class__, borrowing.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Borrowing.objects.filter(id=borrowing.id).exists())

    def test_delete_payment(self):
        payment = Payment.objects.create(
            status=Payment.StatusChoices.PAID,
            type=Payment.TypeChoices.PAYMENT,
            borrowing=self.borrowing,
            session_url="http://example.com/payment-session",
            session_id="fake_session_id",
            money_to_pay=10.00,
        )
        url = detail_url(payment.__class__, payment.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Payment.objects.filter(id=payment.id).exists())

    def test_filter_overdue(self):
        self.user_ = get_user_model().objects.create_user(
            email="123@test.com",
            password="123test",
        )
        self.client.force_authenticate(self.user_)

        borrowing1 = Borrowing.objects.create(**self.defaults)
        borrowing1.expected_return_date = "2023-05-24"
        borrowing1.user = self.user_
        borrowing1.save()
        borrowing2 = Borrowing.objects.create(**self.defaults)
        borrowing2.expected_return_date = "2023-05-21"
        borrowing2.user = self.user_
        borrowing2.save()
        borrowing3 = Borrowing.objects.create(**self.defaults)

        res = self.client.get(BORROWING_URL, {"overdue": "True"})

        serializer1 = BorrowingListSerializer(borrowing1)
        serializer2 = BorrowingListSerializer(borrowing2)
        serializer3 = BorrowingListSerializer(borrowing3)

        self.assertIn(json.dumps(serializer1.data), json.dumps(res.data))
        self.assertIn(json.dumps(serializer2.data), json.dumps(res.data))
        self.assertNotIn(json.dumps(serializer3.data), json.dumps(res.data))


class PaymentTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="123@test.com",
            password="123test",
        )
        self.client.force_authenticate(self.user)

        self.book = sample_book()
        self.borrowing = Borrowing.objects.create(
            borrow_date=datetime.date.today(),
            expected_return_date="2023-05-03",
            actual_return_date=None,
            is_active=True,
            book=self.book,
            user=self.user,
        )

    def test_stripe_session_create(self):
        session_create_mock = mock.MagicMock()
        stripe.checkout.Session.create = session_create_mock

        self.factory = RequestFactory()
        request = self.factory.get("/")
        amount_cents = int(5 * 100)
        url = reverse("library:payment-success")
        success_url = (
            request.build_absolute_uri(url)[:-1] + "?session_id={CHECKOUT_SESSION_ID}"
        )
        cancel_url = request.build_absolute_uri(reverse("library:payment-cancel"))
        self.session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": self.book.title,
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )

        session_create_mock.assert_called_with(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": self.book.title,
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )

    def test_retrieve_payment_detail(self):
        payment = Payment.objects.create(
            status=Payment.StatusChoices.PAID,
            type=Payment.TypeChoices.PAYMENT,
            borrowing=self.borrowing,
            session_url="http://example.com/payment-session",
            session_id="fake_session_id",
            money_to_pay=10.00,
        )
        url = detail_url(payment.__class__, payment.id)
        res = self.client.get(url)

        serializer = PaymentSerializer(payment)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_list_payments(self):
        payment1 = Payment.objects.create(
            status=Payment.StatusChoices.PAID,
            type=Payment.TypeChoices.PAYMENT,
            borrowing=self.borrowing,
            session_url="http://example.com/payment-session1",
            session_id="fake_session_id1",
            money_to_pay=10.00,
        )
        payment2 = Payment.objects.create(
            status=Payment.StatusChoices.PENDING,
            type=Payment.TypeChoices.FINE,
            borrowing=self.borrowing,
            session_url="http://example.com/payment-session2",
            session_id="fake_session_id2",
            money_to_pay=5.00,
        )

        res = self.client.get(reverse("library:payment-list"))

        serializer1 = PaymentSerializer(payment1)
        serializer2 = PaymentSerializer(payment2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data["results"])
        self.assertIn(serializer2.data, res.data["results"])

    def test_pay_money(self):
        borrow_date = datetime.datetime.strptime("2023-07-1", "%Y-%m-%d").date()
        expected_return_date = datetime.datetime.strptime(
            "2023-07-5", "%Y-%m-%d"
        ).date()

        self.borrowing.borrow_date = borrow_date
        self.borrowing.expected_return_date = expected_return_date

        url = reverse("library:payment-success")

        self.assertEqual(round(self.borrowing.pay_money(), 1), 1.8)


class NotificationsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="123@test.com",
            password="123test",
        )
        self.borrowing = Borrowing.objects.create(
            borrow_date=datetime.date.today(),
            expected_return_date="2023-10-31",
            actual_return_date=None,
            is_active=True,
            book=sample_book(),
            user=self.user,
        )

    @patch("library.notifications.bot.send_message")
    def test_new_borrowing_notification(self, send_message_mock):
        new_borrowing(
            self.borrowing.id,
            self.user.id,
            self.borrowing.book.id,
            self.borrowing.book.title,
            self.borrowing.expected_return_date,
        )

        send_message_mock.assert_called_once_with(
            str(BOT_NUMBER),
            f"New borrowing:{self.borrowing.id}, user_id - {self.user.id},\n"
            f" book_id {self.borrowing.book.id} , {self.borrowing.book.title},\n"
            f" expected_return_date - {self.borrowing.expected_return_date}",
            parse_mode="html",
        )

    @patch("library.notifications.bot.send_message")
    def test_overdue_borrowings_notification(self, send_message_mock):
        self.borrowing.expected_return_date = date.today() - timedelta(days=1)
        overdue_borrowing(
            self.borrowing.id,
            self.borrowing.book.id,
            self.borrowing.book.title,
            self.borrowing.expected_return_date,
        )

        send_message_mock.assert_called_once_with(
            str(BOT_NUMBER),
            f"Overdue borrowing: id -{self.borrowing.id}, \n"
            f"book_id {self.borrowing.book.id} ,{self.borrowing.book.title},\n"
            f"expected_return_date - {self.borrowing.expected_return_date}",
        )

    @patch("library.notifications.bot.send_message")
    def test_not_overdue_borrowings_notification(self, send_message_mock):
        self.borrowing.expected_return_date = date.today() + timedelta(days=1)
        overdue_borrowing(
            self.borrowing.id,
            self.borrowing.book.id,
            self.borrowing.book.title,
            self.borrowing.expected_return_date,
        )

        run_sync_with_api()

        send_message_mock.assert_not_called()
