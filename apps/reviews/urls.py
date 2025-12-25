from django.urls import path
from .views import ListingReviewsView

urlpatterns = [
    path("listings/<int:listing_id>/reviews/", ListingReviewsView.as_view(), name="listing-reviews"),
]
