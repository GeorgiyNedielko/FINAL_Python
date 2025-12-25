from rest_framework import serializers
from .models import Listing


class ListingSerializer(serializers.ModelSerializer):
    full_address = serializers.SerializerMethodField()

    avg_rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Listing
        fields = "__all__"
        read_only_fields = ("owner",)

    def get_full_address(self, obj):
        return obj.full_address()
