from rest_framework import serializers
from library.models import Book, Borrowing, Payment
from django.shortcuts import get_object_or_404

import datetime


class BookSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(BookSerializer, self).validate(attrs)
        Book.validate(attrs["inventory"], serializers.ValidationError)

        return data

    class Meta:
        model = Book
        fields = ("id", "title", "cover", "author", "daily_fee", "inventory")


class BorrowingListSerializer(serializers.ModelSerializer):
    book = BookSerializer(many=False)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
        )


class BorrowingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = (
            "id",
            "actual_return_date",
            "book",
        )
        read_only_fields = ("book",)


class BorrowingCreateSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(BorrowingCreateSerializer, self).validate(attrs)

        if datetime.date.today() > attrs["expected_return_date"]:
            raise serializers.ValidationError("Input, please, correct date")
        book = attrs["book"]
        if book.inventory < 1:
            raise serializers.ValidationError("This book unavailable")
        user = attrs["user"]
        if user.borrowing_set.filter(actual_return_date=None):
            raise serializers.ValidationError("Please pay back your previous loans")

        return data

    class Meta:
        model = Borrowing
        fields = [
            "user",
            "book",
            "borrow_date",
            "expected_return_date",
        ]


class PaymentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("borrowing_id", "status", "type")
