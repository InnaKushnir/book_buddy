from django.urls import path, include
from library.views import (
    BookViewSet,
    BorrowingViewSet,
    PaymentViewSet,

)
from library.stripe import order_success
from rest_framework import routers

router = routers.DefaultRouter()
router.register("books", BookViewSet)
router.register("borrowings", BorrowingViewSet)
router.register("payments", PaymentViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "library"
