from django.conf import settings
from django.core.mail import mail_admins
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Listing


def _duplicates(instance: Listing):
    criteria = dict(
        owner_id=instance.owner_id,
        title=instance.title,
        description=instance.description,
        country=instance.country,
        city=instance.city,
        postal_code=instance.postal_code,
        street=instance.street,
        house_number=instance.house_number,
        floor=instance.floor,
        apartment_number=instance.apartment_number,
        price=instance.price,
        currency=instance.currency,
        rooms=instance.rooms,
        housing_type=instance.housing_type,
        parking_type=instance.parking_type,
        is_active=instance.is_active,
    )

    qs = Listing.all_objects.filter(**criteria).exclude(pk=instance.pk)

    if hasattr(Listing, "is_deleted"):
        qs = qs.filter(is_deleted=False)

    return qs


@receiver(post_save, sender=Listing)
def notify_admin_on_create_and_duplicates(sender, instance: Listing, created: bool, **kwargs):
    # Новое объявление
    if created:
        subject = "New Listing created"
        message = (
            f"New listing has been created.\n\n"
            f"Listing ID: {instance.id}\n"
            f"Owner ID: {instance.owner_id}\n"
            f"Title: {instance.title}\n"
            f"Address: {instance.full_address()}\n"
            f"Price: {instance.price} {instance.currency}\n"
            f"Housing type: {instance.housing_type}\n"
            f"Rooms: {instance.rooms}\n"
            f"Active: {instance.is_active}\n"
        )

        _safe_mail_admins(subject, message)

    # Проверка дубликатов
    dup_qs = _duplicates(instance)
    if dup_qs.exists():
        subject = "Duplicate Listing detected"
        message = (
            f"Duplicate listing detected.\n\n"
            f"Listing ID: {instance.id}\n"
            f"Owner ID: {instance.owner_id}\n"
            f"Title: {instance.title}\n"
            f"Address: {instance.full_address()}\n"
            f"Price: {instance.price} {instance.currency}\n"
            f"Duplicate IDs: {list(dup_qs.values_list('id', flat=True)[:10])}\n"
        )

        _safe_mail_admins(subject, message)


def _safe_mail_admins(subject: str, message: str):

    try:
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=False,
        )
    except Exception:

        pass
