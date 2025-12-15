from celery import shared_task

from  .models import Listing

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