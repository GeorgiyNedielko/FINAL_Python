from django.urls import path

from .api import ListingListAPIView

urlpatterns = [
    path("api/listings/", ListingListAPIView.as_view(), name="listings_api"),
]