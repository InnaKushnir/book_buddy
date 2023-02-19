from django.shortcuts import render
from library.models import Book, Borrowing
from . serializers import (
    BookSerializer,
    BorrowingListSerializer,
    BorrowingSerializer,
    BorrowingUpdateSerializer,
    BorrowingCreateSerializer
)
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import mixins, viewsets



def index(request):
    return render(request)

class BookViewSet(
    viewsets.ModelViewSet
):
    queryset = Book. objects.all()
    serializer_class = BookSerializer

class BorrowingViewSet(
    viewsets.ModelViewSet
):
    queryset = Borrowing. objects.all()

    def get_serializer_class(self):
        if self.action == "list" or self.action == "retrieve":
            return BorrowingListSerializer
        elif self.action == "update":
            return BorrowingUpdateSerializer
        elif self.action == "create":
            return BorrowingCreateSerializer
        return BorrowingSerializer
