from rest_framework import serializers
from library.models import Book, Borrowing
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



class BorrowingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Borrowing
        fields = ("id", "borrow_date", "expected_return_date", "actual_return_date", "book")


class BorrowingListSerializer(BorrowingSerializer):
    book= BookSerializer(many=False)

    class Meta:
        model = Borrowing
        fields = ("id", "borrow_date","expected_return_date","actual_return_date", "book")
        read_only_fields = ("book",)

class BorrowingUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Borrowing
        fields = ("actual_return_date", "book", "is_active" )
        read_only_fields = ("book",)

    def validate(self, attrs):
        data = super(BorrowingUpdateSerializer, self).validate(attrs)
        if attrs["actual_return_date"] < self.instance.borrow_date:
            raise serializers.ValidationError(
                "Input, please, correct date"
            )
        return_date = (attrs["actual_return_date"])

        if return_date is not None:
            borrowing = get_object_or_404(Borrowing, pk=self.instance.id)

            borrowing.is_active = False
            borrowing.save()
            print(borrowing.is_active)

            book_return = borrowing.book
            book_return.inventory += 1
            book_return.save()

        return data


class BorrowingCreateSerializer(serializers.ModelSerializer):

    def validate(self, attrs):
        data = super(BorrowingCreateSerializer, self).validate(attrs)

        if datetime.date.today() > attrs["expected_return_date"]:
            raise serializers.ValidationError(
                "Input, please, correct date"
            )
        book = attrs["book"]
        if book.inventory < 1:
            raise serializers.ValidationError(
                "This book unavailable"
            )
        return data


    class Meta:
        model = Borrowing
        fields = ["book", "borrow_date", "expected_return_date", ]
