from django.contrib import admin

from django.contrib import admin

from .models import (
    Book,
    Payment,
    Borrowing,
)

admin.site.register(Book)
admin.site.register(Payment)
admin.site.register(Borrowing)
