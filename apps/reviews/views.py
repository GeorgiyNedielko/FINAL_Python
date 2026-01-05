# apps/reviews/views.py

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions

from apps.listings.models import Listing
from apps.bookings.models import Booking
from apps.reviews.models import Review
from apps.reviews.serializers import (
    ReviewCreateSerializer,
    ReviewListSerializer,
    TenantReviewCreateSerializer,
)


class ListingReviewsView(generics.ListCreateAPIView):
    permission_classes = [permissions.AllowAny]

    def get_listing(self):
        return get_object_or_404(Listing, id=self.kwargs["listing_id"])

    def get_queryset(self):
        return Review.objects.filter(listing=self.get_listing()).select_related("author")

    def get_serializer_class(self):
        return ReviewCreateSerializer if self.request.method == "POST" else ReviewListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["listing"] = self.get_listing()
        return ctx


class TenantReviewCreateView(generics.CreateAPIView):
    serializer_class = TenantReviewCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_booking(self):
        return get_object_or_404(Booking, id=self.kwargs["booking_id"])

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["booking"] = self.get_booking()
        return ctx
