from library.notifications import over_, not_overdue
from library.models import Book, Borrowing
from celery import shared_task
import datetime


@shared_task
def run_sync_with_api() -> list:
    overdue = Borrowing.objects.filter(
        expected_return_date__lt=datetime.date.today()
    ).filter(actual_return_date=None)
    if overdue:
        for over in overdue:
            over_(over.id, over.book.id, over.book.title, over.expected_return_date)
    else:
        not_overdue()
