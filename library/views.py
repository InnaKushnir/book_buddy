from django.shortcuts import render
from django.contrib.auth import get_user_model
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
from rest_framework.permissions import IsAuthenticated




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
    permission_classes = (IsAuthenticated, )

    def get_serializer_class(self):
        if self.action == "list" or self.action == "retrieve":
            return BorrowingListSerializer
        elif self.action == "update":
            return BorrowingUpdateSerializer
        elif self.action == "create":
            return BorrowingCreateSerializer
        return BorrowingSerializer

    def get_queryset(self):
        return Borrowing.objects.filter(user=self.request.user)


    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
