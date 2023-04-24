from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from library.models import Book, Borrowing
from library.serializers import BookSerializer, BorrowingListSerializer
from django.contrib.auth import get_user_model

BORROWING_URL = reverse("library:borrowing-list")
BOOK_URL = reverse("library:book-list")

def detail_url(borrowing_id: int):
    return reverse("library:borrowing-detail", args=[borrowing_id])
def sample_book(**kwargs):
    defaults = {
        "author": "Jerome K. Jerome",
        "title": "Three men in a boat",
        "cover" : "soft",
        "daily_fee": 0.15,
        "inventory": 20
    }
    defaults.update(kwargs)
    return Book.objects.create(**defaults)

def sample_borrowing(**kwargs):
    defaults = {
        "borrow_date": "2023-04-24",
        "expected_return_date": "2023-04-30",
        "actual_return_date": None,
        "is_active": True,
        "book": sample_book(),
        "user": self.user
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
        self.assertEqual(res.data, serializer.data)


class AuthenticateBorrowingTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="12345@test.com",
            password="12345test"
        )
        self.client.force_authenticate(self.user)

        self.defaults = {
            "borrow_date": "2023-04-17",
            "expected_return_date": "2023-04-28",
            "actual_return_date": None,
            "is_active": True,
            "book": sample_book(),
            "user": self.user
        }
        borrowing = Borrowing.objects.create(**self.defaults)

    def test_list_borrowing(self):
        res = self.client.get(BORROWING_URL)
        borrowings = Borrowing.objects.all()
        serializer = BorrowingListSerializer(borrowings, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_borrowings_by_overdue(self):
        borrowing1 = Borrowing.objects.create(**self.defaults)
        borrowing1.expected_return_date = "2023-04-23"
        borrowing1.save()
        borrowing2 = Borrowing.objects.create(**self.defaults)
        borrowing2.expected_return_date = "2023-04-21"
        borrowing2.save()
        borrowing3 = Borrowing.objects.create(**self.defaults)

        res = self.client.get(BORROWING_URL, {"overdue": "True"})

        serializer1 = BorrowingListSerializer(borrowing1)
        serializer2 = BorrowingListSerializer(borrowing2)
        serializer3= BorrowingListSerializer(borrowing3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_borrowing_detail(self):
        borrowing = Borrowing.objects.create(**self.defaults)
        url = detail_url(borrowing.id)
        res = self.client.get(url)

        serializer = BorrowingListSerializer(borrowing)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
