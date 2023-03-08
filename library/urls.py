from django.urls import path, include
from library.views import BookViewSet, BorrowingViewSet, PaymentViewSet, payment_success
from rest_framework import routers

router = routers.DefaultRouter()
router.register("books", BookViewSet)
router.register("borrowings", BorrowingViewSet)
router.register("payments", PaymentViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("payments/", PaymentViewSet.as_view({'get': 'list'}), name="payment-list"),
    path("payments/create", PaymentViewSet.as_view({"post": "create"}), name="payment-create"),
    path("payments/success/", payment_success, name='payment-success'),
    path("payments/<int:pk>/", PaymentViewSet.as_view({'get': 'list'}), name="payment-detail"),
               ]

print(list(router.urls))

app_name = "library"
