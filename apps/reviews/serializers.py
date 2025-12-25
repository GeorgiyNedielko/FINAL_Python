

from apps.reviews.models import Review
from apps.bookings.models import Booking

from rest_framework import serializers
from .models import Listing


class ListingSerializer(serializers.ModelSerializer):
    avg_rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Listing
        fields = [

            "id",
            "title",
            "description",
            "price",
            "currency",
            "rooms",
            "housing_type",
            "parking_type",
            "city",
            "is_active",
            "created_at",


            "avg_rating",
            "reviews_count",
        ]

class ReviewCreateSerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Review
        fields = ["id", "booking_id", "rating", "text", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_booking_id(self, booking_id):
        request = self.context["request"]
        listing = self.context["listing"]

        try:
            booking = Booking.objects.select_related("listing").get(id=booking_id)
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking не найден.")

        if booking.listing_id != listing.id:
            raise serializers.ValidationError(
                "Этот booking не относится к данному объявлению."
            )
        #
        # if getattr(booking, "status", None) != "confirmed":
        #     raise serializers.ValidationError(
        #         "Отзыв можно оставить только по подтверждённой брони."
        #     )
        status_value = getattr(booking, "status", None)
        if status_value not in ("confirmed", "approved"):
            raise serializers.ValidationError(
                "Отзыв можно оставить только по подтверждённой брони."
            )

        # end_date = getattr(booking, "end_date", None)
        # if end_date is None:
        #     raise serializers.ValidationError(
        #         "У booking нет end_date — проверь модель bookings."
        #     )
        #
        # if end_date >= timezone.localdate():
        #     raise serializers.ValidationError(
        #         "Отзыв можно оставить только после завершения проживания."
        #     )

        status_value = getattr(booking, "status", None)
        if status_value not in ("confirmed", "approved"):
            raise serializers.ValidationError(
                "Отзыв можно оставить только по подтверждённой брони."
            )

        if hasattr(booking, "review"):
            raise serializers.ValidationError(
                "По этой брони отзыв уже оставлен."
            )

        self.context["booking_obj"] = booking
        return booking_id

    def create(self, validated_data):
        request = self.context["request"]
        listing = self.context["listing"]
        booking = self.context["booking_obj"]

        validated_data.pop("booking_id", None)

        return Review.objects.create(
            listing=listing,
            booking=booking,
            author=request.user,
            **validated_data
        )


class ReviewListSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "author_email", "rating", "text", "created_at"]
