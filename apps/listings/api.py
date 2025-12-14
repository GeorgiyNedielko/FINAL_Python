from decimal import Decimal, InvalidOperation

from django.db.models import Q
from rest_framework.generics import ListAPIView
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import Listing
from .serializers import ListingSerializer

from django.utils.dateparse import parse_date
from datetime import datetime, time
from django.utils.timezone import make_aware

def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _to_decimal(v):
    try:
        return Decimal(v)
    except (TypeError, ValueError, InvalidOperation):
        return None


class ListingListAPIView(ListAPIView):
    serializer_class = ListingSerializer

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description"]

    ordering_fields = ["price", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Listing.objects.filter(is_active=True)


        if hasattr(Listing, "is_deleted"):
            qs = qs.filter(is_deleted=False)

        p = self.request.query_params

        date_from = parse_date(p.get("date_from"))
        if date_from:
            qs = qs.filter(
                created_at__gte=make_aware(datetime.combine(date_from, time.min))
            )

        date_to = parse_date(p.get("date_to"))
        if date_to:
            qs = qs.filter(
                created_at__lte=make_aware(datetime.combine(date_to, time.max))
            )


        price_min = _to_decimal(p.get("price_min"))
        if price_min is not None:
            qs = qs.filter(price__gte=price_min)

        price_max = _to_decimal(p.get("price_max"))
        if price_max is not None:
            qs = qs.filter(price__lte=price_max)


        currency = p.get("currency")
        if currency:
            qs = qs.filter(currency=currency)


        rooms_min = _to_int(p.get("rooms_min"))
        if rooms_min is not None:
            qs = qs.filter(rooms__gte=rooms_min)

        rooms_max = _to_int(p.get("rooms_max"))
        if rooms_max is not None:
            qs = qs.filter(rooms__lte=rooms_max)


        housing_type = p.get("housing_type")
        if housing_type:
            qs = qs.filter(housing_type=housing_type)


        city = p.get("city")
        if city:
            qs = qs.filter(city__icontains=city)


        district = p.get("district")
        if district:
            qs = qs.filter(Q(street__icontains=district) | Q(postal_code__icontains=district))


        country = p.get("country")
        if country:
            qs = qs.filter(country__icontains=country)

        return qs
