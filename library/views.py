from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from library.models import Book, Borrowing
from . serializers import (
    BookSerializer,
    BorrowingListSerializer,
    BorrowingUpdateSerializer,
    BorrowingCreateSerializer
)
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from . notifications import new_borrowing


import datetime

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
        if self.action == "update":
            return BorrowingUpdateSerializer
        elif self.action == "create":
            return BorrowingCreateSerializer
        return BorrowingListSerializer

    def get_queryset(self):
        queryset = Borrowing.objects.all()

        is_active_ = self.request.query_params.get("is_active")
        user_id = self.request.query_params.get("user_id")
        overdue = self.request.query_params.get("overdue")

        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        if (is_active_ is not None) and (user_id is not None
        ) and self.request.user.is_staff:
            if str(is_active_)=="False":

                queryset = queryset.filter(is_active=False).filter(user_id=user_id)
            else:
                queryset = queryset.filter(is_active=True).filter(user_id=user_id)
        if overdue:
            queryset = queryset.filter(
                expected_return_date__lte=datetime.date.today()).filter(
                actual_return_date=None
            )

        return queryset

    def update(self, request, pk=None):

        borrowing = Borrowing.objects.get(pk=pk)
        borrowing.actual_return_date =datetime.date.today()
        borrowing.is_active = False
        book = borrowing.book
        book.inventory += 1

        serializer = BorrowingUpdateSerializer(
            borrowing,
            many=False,
            partial=True,
            data= {'actual_return_date': datetime.date.today()}
        )

        serializer.is_valid()
        borrowing.save()
        book.save()

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


