from django.urls import path, include
from library.views import index, BookViewSet, BorrowingViewSet
from rest_framework import routers

router = routers.DefaultRouter()
router.register("books", BookViewSet)
router.register("borrowings", BorrowingViewSet)

urlpatterns = [
    path("", include(router.urls))
]

app_name = "library"
