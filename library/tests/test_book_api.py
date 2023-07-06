import os
from datetime import date
import datetime
from decimal import Decimal
import stripe
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest import mock
from django.test import RequestFactory
from library.models import Book, Borrowing, Payment
from library.views import BorrowingViewSet
from library.serializers import BookSerializer, BorrowingListSerializer
from django.contrib.auth import get_user_model
import json


stripe.api_key = os.getenv("STRIPE_TEST_SECRET")
BORROWING_URL = reverse("library:borrowing-list")
BOOK_URL = reverse("library:book-list")
PAYMENT_URL = reverse("library:payment-success")


def detail_url(borrowing_id: int):
    return reverse("library:borrowing-detail", args=[borrowing_id])


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
        url = detail_url(borrowing.id)
        res = self.client.get(url)

        serializer = BorrowingListSerializer(borrowing)
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
        borrowing = Borrowing.objects.create(**self.defaults)

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

    def test_pay_money(self):
        borrow_date = datetime.datetime.strptime("2023-07-1", "%Y-%m-%d").date()
        expected_return_date = datetime.datetime.strptime(
            "2023-07-5", "%Y-%m-%d"
        ).date()

        self.borrowing.borrow_date = borrow_date
        self.borrowing.expected_return_date = expected_return_date

        url = reverse("library:payment-success")

        self.assertEqual(round(self.borrowing.pay_money(), 1), 0.9)
