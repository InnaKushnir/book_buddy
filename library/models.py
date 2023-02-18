from django.db import models

class Book(models.Model):

    class CoverChoices(models.TextChoices):
        HARD = "HARD"
        SOFT = "SOFT"

    title = models.CharField(max_length=63)
    author =models.CharField(max_length=124)
    cover = models.CharField(max_length=10, choices=CoverChoices.choices)
    inventory = models.IntegerField()
    daily_fee = models.DecimalField(max_digits=6, decimal_places=3)

class Borrowing(models.Model):
    borrow_date = models.DateField()
    expected_return_date = models.DateField(auto_now=False)
    actual_return_date = models.DateField(auto_now=False)
    book_id = models.ForeignKey(Book,on_delete=models.CASCADE, related_name="borrowings")


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

