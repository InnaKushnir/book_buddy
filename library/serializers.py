import datetime

from library.models import Book, Borrowing, Payment
from rest_framework import serializers


class BookSerializer(serializers.ModelSerializer):
    def validate_inventory(self, attrs):
        if attrs < 1:
            raise serializers.ValidationError(
                "Inventory should be greater than or equal to 1"
            )
        return attrs

    class Meta:
        model = Book
        fields = ("id", "title", "cover", "author", "daily_fee", "inventory")


class BorrowingListSerializer(serializers.ModelSerializer):
    book = BookSerializer(many=False)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "user",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "is_active",
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
    def validate_expected_return_date(self, attrs):
        if datetime.date.today() > attrs:
            raise serializers.ValidationError("Please, enter a correct date")
        return attrs

    def validate_book(self, attrs):
        if attrs.inventory < 1:
            raise serializers.ValidationError("This book is unavailable")
        return attrs

    def validate_user(self, attrs):
        if attrs.borrowing_set.filter(actual_return_date=None).exists():
            raise serializers.ValidationError("Please pay back your previous loans")
        return attrs

    class Meta:
        model = Borrowing
        fields = [
            "user",
            "book",
            "borrow_date",
            "expected_return_date",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "borrowing",
            "status",
            "type",
            "session_url",
            "session_id",
            "money_to_pay",
        )
