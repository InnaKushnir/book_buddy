from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

import datetime

class Book(models.Model):
    class CoverChoices(models.TextChoices):
        HARD = "HARD"
        SOFT = "SOFT"

    title = models.CharField(max_length=63)
    author = models.CharField(max_length=124)
    cover = models.CharField(max_length=10, choices=CoverChoices.choices)
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(max_digits=6, decimal_places=3)


    @staticmethod
    def validate(inventory: int, error_to_raise):
        if inventory < 0:
            raise error_to_raise(
                "Input positive numeric "
            )

    def clean(self):
        Book.validate(self.inventory, ValidationError)

    def __str__(self):
        return str(self.title)


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField(auto_now=False)
    actual_return_date = models.DateField(auto_now=False, null=True, blank=True)
    book_id = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="borrowings"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )

    @property
    def book(self):
        return self.book_id




    def clean(self):
        borrow_date = datetime.date.today()
        borrow_date = borrow_date.strftime('%Y-%m-%d')
        if datetime.date.today() > self.expected_return_date:
            raise ValidationError(
                "Input, please, correct date"
            )

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        self.full_clean()
        return super(Borrowing, self).save(
            force_insert, force_update, using, update_fields
        )

class Payment(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "PENDING"
        PAID = "PAID"

    class TypeChoices(models.TextChoices):
        PAYMENT = "PAYMENT"
        FINE = "FINE"

    status = models.CharField(max_length=10, choices=StatusChoices.choices)
    type = models.CharField(max_length=10, choices=TypeChoices.choices)
    borrowing_id = models.ForeignKey(Borrowing, on_delete=models.CASCADE)
    session_url = models.URLField()
    session_id = models.IntegerField()
    money_to_pay = models.DecimalField(max_digits=6, decimal_places=3)
