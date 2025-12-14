from rest_framework import serializers
from .models import Listing


class ListingSerializer(serializers.ModelSerializer):
    full_address = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "description",
            "country",
            "city",
            "postal_code",
            "street",
            "house_number",
            "floor",
            "apartment_number",
            "price",
            "currency",
            "rooms",
            "housing_type",
            "parking_type",
            "is_active",
            "created_at",
            "updated_at",
            "full_address",
        ]

    def get_full_address(self, obj):
        return obj.full_address()
