import logging

from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import Booking

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Booking)
def notify_on_booking_created(sender, instance: Booking, created: bool, **kwargs):
    if not created:
        return

    try:
        listing = instance.listing
        landlord_email = getattr(listing.owner, "email", None)

        if not landlord_email:
            logger.warning("Booking %s created but landlord email not found", instance.id)
            return

        subject = f"New booking request (#{instance.id})"
        message = (
            f"New booking created.\n\n"
            f"Booking ID: {instance.id}\n"
            f"Listing ID: {listing.id}\n"
            f"Tenant ID: {instance.tenant_id}\n"
            f"Dates: {instance.date_from} — {instance.date_to}\n"
            f"Status: {instance.status}\n"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[landlord_email],
            fail_silently=False,
        )

    except Exception:
        logger.exception("Failed to send booking created email")
