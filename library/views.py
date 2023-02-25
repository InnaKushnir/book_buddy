from django.shortcuts import render, get_object_or_404
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
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser



class BookViewSet(
    viewsets.ModelViewSet
):
    queryset = Book. objects.all()
    serializer_class = BookSerializer
    permission_classes = (AllowAny,)

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminUser()]
        return super().get_permissions()


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


    def perform_create(self, serializer, **kwargs):

        serializer.save(user=self.request.user)
        self.change_inventory()


    def change_inventory(self):
        book_id = self.request.data["book"]
        book = get_object_or_404(Book, pk=book_id)
        book.inventory -= 1
        book.save()
