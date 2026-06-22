import pytest
from django.contrib.auth import get_user_model

from apps.listings.models import Listing
from apps.listings.services import filter_listings, base_listing_queryset
from decimal import Decimal

User = get_user_model()


@pytest.mark.django_db
def test_filter_by_city():
    user = User.objects.create_user(email="o@t.com", username="o", password="x", role="landlord")
    Listing.objects.create(
        owner=user,
        title="Moscow flat",
        description="d",
        city="Moscow",
        price=Decimal("50"),
        rooms=1,
        housing_type="apartment",
    )
    Listing.objects.create(
        owner=user,
        title="Paris flat",
        description="d",
        city="Paris",
        price=Decimal("50"),
        rooms=1,
        housing_type="apartment",
    )
    qs = filter_listings(base_listing_queryset(), {"q": "Moscow"})
    assert qs.count() == 1
