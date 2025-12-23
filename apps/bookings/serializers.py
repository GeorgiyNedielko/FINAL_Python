from django.utils import timezone
from rest_framework import serializers

from .models import Booking


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ("id", "listing", "date_from", "date_to", "status", "created_at")
        read_only_fields = ("id", "status", "created_at")

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        date_from = attrs["date_from"]
        date_to = attrs["date_to"]
        listing = attrs["listing"]

        if date_from >= date_to:
            raise serializers.ValidationError("date_to должен быть позже date_from.")

        if not listing.is_active:
            raise serializers.ValidationError("Объявление не активно.")

        if listing.owner_id == user.id:
            raise serializers.ValidationError("Нельзя бронировать своё объявление.")

        overlap = Booking.objects.filter(
            listing_id=listing.id,
            status__in=[Booking.Status.PENDING, Booking.Status.APPROVED],
            date_from__lt=date_to,
            date_to__gt=date_from,
        ).exists()

        if overlap:
            raise serializers.ValidationError("Выбранные даты пересекаются с другим бронированием.")

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return Booking.objects.create(tenant=user, **validated_data)


class BookingSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_owner_id = serializers.IntegerField(source="listing.owner_id", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "listing",
            "listing_title",
            "listing_owner_id",
            "tenant",
            "date_from",
            "date_to",
            "status",
            "created_at",
            "updated_at",
            "decided_at",
            "decided_by",
            "canceled_at",
        )
        read_only_fields = fields
