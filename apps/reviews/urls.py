# apps/reviews/urls.py
from django.urls import path

from .views import ListingReviewsView, TenantReviewCreateView

urlpatterns = [
    path(
        "listings/<int:listing_id>/reviews/",
        ListingReviewsView.as_view(),
        name="listing-reviews",
    ),
    path(
        "bookings/<int:booking_id>/tenant-review/",
        TenantReviewCreateView.as_view(),
        name="tenant-review-create",
    ),
]
