import datetime

from celery import shared_task
from library.models import Borrowing
from library.notifications import overdue_borrowing, not_overdue


@shared_task
def run_sync_with_api() -> list:
    overdue = Borrowing.objects.filter(
        expected_return_date__lt=datetime.date.today()
    ).filter(actual_return_date=None)
    if overdue:
        for over in overdue:
            overdue_borrowing(over.id, over.book.id, over.book.title, over.expected_return_date)
    else:
        not_overdue()
