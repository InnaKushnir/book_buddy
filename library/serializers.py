from rest_framework import serializers
from library.models import Book, Borrowing

import datetime


class BookSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(BookSerializer, self).validate(attrs)
        Book.validate(attrs["inventory"], serializers.ValidationError)

        return data
    class Meta:
        model = Book
        fields = ("id", "title", "cover", "author", "daily_fee", "inventory")



class BorrowingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Borrowing
        fields = ("id", "borrow_date", "expected_return_date", "actual_return_date", "book_id")


class BorrowingListSerializer(BorrowingSerializer):
    book= BookSerializer(many=False)

    class Meta:
        model = Borrowing
        fields = ("id", "borrow_date","expected_return_date","actual_return_date", "book")
        read_only_fields = ("book",)

class BorrowingUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Borrowing
        fields = ("actual_return_date", "book_id" )
        read_only_fields = ("book_id",)

class BorrowingCreateSerializer(serializers.ModelSerializer):

    def validate(self, attrs):
        data = super(BorrowingCreateSerializer, self).validate(attrs)
        borrow_date = (attrs["expected_return_date"]).strftime('%Y-%m-%d')
        if datetime.date.today() > attrs["expected_return_date"]:
            raise serializers.ValidationError(
                "Input, please, correct date"
            )
        print(attrs["book_id"])
        book = attrs["book_id"]
        if book.inventory < 1:
            raise serializers.ValidationError(
                "This book unavailable"
            )
        return data


    class Meta:
        model = Borrowing
        fields = ["book_id", "borrow_date", "expected_return_date", ]
