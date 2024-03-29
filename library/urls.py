from django.urls import path, include
from library.stripe import order_success
from library.views import (
    BookViewSet,
    BorrowingViewSet,
    PaymentViewSet,
)
from rest_framework import routers

router = routers.DefaultRouter()
router.register("books", BookViewSet)
router.register("borrowings", BorrowingViewSet)
router.register("payments", PaymentViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("order/success", order_success, name="order_success"),
]

app_name = "library"
