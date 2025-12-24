import re

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.common.redis_client import get_redis_client
from .models import Listing, ListingViewStat




def _duplicates_for_listing(listing: Listing):
    criteria = dict(
        owner_id=listing.owner_id,
        title=listing.title,
        description=listing.description,
        country=listing.country,
        city=listing.city,
        postal_code=listing.postal_code,
        street=listing.street,
        house_number=listing.house_number,
        floor=listing.floor,
        apartment_number=listing.apartment_number,
        price=listing.price,
        currency=listing.currency,
        rooms=listing.rooms,
        housing_type=listing.housing_type,
        parking_type=listing.parking_type,
        is_active=listing.is_active,
    )

    qs = Listing.all_objects.filter(**criteria).exclude(pk=listing.pk)

    if hasattr(Listing, "is_deleted"):
        qs = qs.filter(is_deleted=False)

    return qs


@shared_task
def delete_listing_if_still_duplicate(listing_id: int):
    try:
        listing = Listing.all_objects.get(pk=listing_id)
    except Listing.DoesNotExist:
        return

    if not _duplicates_for_listing(listing).exists():
        return

    if hasattr(Listing, "_meta") and any(f.name == "is_deleted" for f in Listing._meta.fields):
        Listing.all_objects.filter(pk=listing_id, is_deleted=False).update(is_deleted=True)
        return

    Listing.all_objects.filter(pk=listing_id).delete()




KEY_RE = re.compile(r"^listing:(\d+):views$")


@shared_task(bind=True, ignore_result=True)
def track_listing_view(self, listing_id: int, user_id: int | None = None, owner_id: int | None = None) -> None:
    """
    Вызываем на detail endpoint.
    Пишем счётчик просмотров в Redis.
    """
    # если это владелец — не считаем (если owner_id передали)
    if user_id and owner_id and user_id == owner_id:
        return

    r = get_redis_client()

    r.incr(f"listing:{listing_id}:views", 1)

    day = timezone.localdate().isoformat()
    r.incr(f"listing:{listing_id}:views:{day}", 1)


@shared_task(bind=True)
def flush_listing_views_to_db(self, batch_size: int = 500) -> dict:
    """
    Раз в минуту (celery beat):
    - ищет listing:*:views
    - атомарно забирает значение и удаляет ключ (GET+DEL в pipeline)
    - прибавляет к ListingViewStat.views_total
    """
    r = get_redis_client()

    cursor = 0
    listings_updated = 0
    total_increment = 0
    keys_found = 0

    while True:
        cursor, keys = r.scan(cursor=cursor, match="listing:*:views", count=batch_size)

        if keys:
            keys_found += len(keys)

        for key in keys:

            m = KEY_RE.match(key)
            if not m:
                continue

            listing_id = int(m.group(1))

            pipe = r.pipeline()
            pipe.get(key)
            pipe.delete(key)
            value, _ = pipe.execute()

            if not value:
                continue

            try:
                delta = int(value)
            except ValueError:
                continue


            with transaction.atomic():
                ListingViewStat.objects.get_or_create(
                    listing_id=listing_id,
                    defaults={"views_total": 0},
                )
                ListingViewStat.objects.filter(listing_id=listing_id).update(
                    views_total=F("views_total") + delta
                )

            listings_updated += 1
            total_increment += delta

        if cursor == 0:
            break

    return {
        "status": "ok",
        "keys_found": keys_found,
        "listings_updated": listings_updated,
        "total_increment": total_increment,
    }
