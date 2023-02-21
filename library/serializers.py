from rest_framework import serializers
from library.models import Book, Borrowing


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

class BorrowingUpdateSerializer(BorrowingSerializer):
    class Meta:
        model = Borrowing
        fields = ("actual_return_date", )

class BorrowingCreateSerializer(BorrowingSerializer):
    class Meta:
        model = Borrowing
        fields = ("book_id","borrow_date","expected_return_date",)
