from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Count, Q, Value
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date

from apps.listings.models import Listing, SearchQuery


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


def base_listing_queryset():
    return (
        Listing.objects.filter(is_active=True, is_deleted=False)
        .select_related("owner")
        .prefetch_related("images", "amenities")
        .annotate(
            avg_rating=Coalesce(Avg("reviews__rating"), 0.0),
            reviews_count=Count("reviews", distinct=True),
        )
    )


def filter_listings(qs, params, user=None):
    q = params.get("q") or params.get("city")
    if q:
        q_clean = str(q).strip()
        if q_clean:
            SearchQuery.objects.create(
                user=user if user and user.is_authenticated else None,
                query=q_clean[:255],
            )
        qs = qs.filter(
            Q(title__icontains=q_clean)
            | Q(description__icontains=q_clean)
            | Q(city__icontains=q_clean)
            | Q(country__icontains=q_clean)
            | Q(street__icontains=q_clean)
        )

    country = params.get("country")
    if country:
        qs = qs.filter(country__icontains=country)

    housing_type = params.get("housing_type")
    if housing_type:
        qs = qs.filter(housing_type=housing_type)

    rooms_min = _to_int(params.get("rooms_min"))
    if rooms_min is not None:
        qs = qs.filter(rooms__gte=rooms_min)

    guests = _to_int(params.get("guests"))
    if guests is not None:
        qs = qs.filter(max_guests__gte=guests)

    price_min = _to_decimal(params.get("price_min"))
    if price_min is not None:
        qs = qs.filter(price__gte=price_min)

    price_max = _to_decimal(params.get("price_max"))
    if price_max is not None:
        qs = qs.filter(price__lte=price_max)

    currency = params.get("currency")
    if currency:
        qs = qs.filter(currency=currency)

    date_from = params.get("date_from") or params.get("check_in")
    date_to = params.get("date_to") or params.get("check_out")
    if date_from and date_to:
        df = parse_date(str(date_from))
        dt = parse_date(str(date_to))
        if df and dt and df < dt:
            qs = qs.exclude(
                bookings__date_from__lt=dt,
                bookings__date_to__gt=df,
                bookings__status__in=["pending", "approved"],
            ).distinct()

    amenity_ids = params.getlist("amenities") if hasattr(params, "getlist") else []
    if not amenity_ids and params.get("amenities"):
        amenity_ids = [params.get("amenities")]
    amenity_ids = [int(x) for x in amenity_ids if str(x).isdigit()]
    for aid in amenity_ids:
        qs = qs.filter(amenities__id=aid)

    sort = params.get("sort", "popular")
    if sort == "price_asc":
        qs = qs.order_by("price", "-created_at")
    elif sort == "price_desc":
        qs = qs.order_by("-price", "-created_at")
    elif sort == "rating":
        qs = qs.order_by("-avg_rating", "-reviews_count")
    else:
        qs = qs.order_by("-reviews_count", "-avg_rating", "-created_at")

    return qs
