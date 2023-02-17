from django.db import models

class Book(models.Model):

    class CoverChoices(models.TextChoices):
        HARD = "Hard"
        SOFT = "Soft"

    title = models.CharField(max_length=63)
    author =models.ManyToManyField(Author, related_name="books")
    cover = models.CharField(max_length=10, choices=CoverChoices.choices)
    inventory = models.IntegerField()
    daily_fee = models.DecimalField()

class Borrowing(models.Model):
    borrow_date = models.DateField()
    expected_return_date = models.DateField(auto_now=False)
    actual_return_date = models.DateField(auto_now=False)
    book_id = models.IntegerField()
    user_id = models.IntegerField()

