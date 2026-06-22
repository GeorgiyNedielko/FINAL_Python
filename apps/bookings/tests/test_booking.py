from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.bookings.models import Booking
from apps.listings.models import Listing

User = get_user_model()


@pytest.fixture
def landlord(db):
    return User.objects.create_user(
        email="landlord@test.com",
        username="landlord",
        password="pass12345",
        role=User.Role.LANDLORD,
    )


@pytest.fixture
def tenant(db):
    return User.objects.create_user(
        email="tenant@test.com",
        username="tenant",
        password="pass12345",
        role=User.Role.TENANT,
    )


@pytest.fixture
def listing(landlord):
    return Listing.objects.create(
        owner=landlord,
        title="Test flat",
        description="Nice place",
        city="Berlin",
        country="DE",
        price=Decimal("100.00"),
        currency="EUR",
        rooms=2,
        housing_type=Listing.HousingType.APARTMENT,
        min_nights=2,
    )


@pytest.mark.django_db
def test_price_for_stay_with_fee(listing):
    listing.platform_fee_percent = Decimal("10")
    listing.save()
    total = listing.price_for_stay(date(2026, 7, 1), date(2026, 7, 4))
    assert total == Decimal("330.00")


@pytest.mark.django_db
def test_booking_overlap_validation(listing, tenant):
    Booking.objects.create(
        listing=listing,
        tenant=tenant,
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 5),
        status=Booking.Status.APPROVED,
        total_price=Decimal("400"),
    )
    overlap = Booking.objects.filter(
        listing=listing,
        status__in=[Booking.Status.PENDING, Booking.Status.APPROVED],
        date_from__lt=date(2026, 8, 3),
        date_to__gt=date(2026, 8, 2),
    ).exists()
    assert overlap
