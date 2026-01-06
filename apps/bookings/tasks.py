from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Booking


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_booking_created_email(self, booking_id: int):
    booking = (
        Booking.objects
        .select_related("tenant", "listing", "listing__owner")
        .get(id=booking_id)
    )

    subject = f"Новая бронь (ID {booking.id})"

    msg = (
        f"Создана новая бронь.\n\n"
        f"Объявление: {booking.listing.title}\n"
        f"Арендатор: {booking.tenant.email}\n"
        f"Дата заезда: {booking.date_from}\n"
        f"Дата выезда: {booking.date_to}\n"
        f"Статус: {booking.status}\n"
    )

    recipients = [booking.tenant.email, booking.listing.owner.email]
    recipients = [x for x in recipients if x]

    if not recipients:
        return {"ok": False, "reason": "no_recipients"}

    send_mail(subject, msg, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
    return {"ok": True, "recipients": recipients}

def _recipients_with_admin_copy(booking: Booking):
    recipients = [booking.tenant.email, booking.listing.owner.email]
    recipients = [x for x in recipients if x]

    admin_copy = getattr(settings, "EMAIL_HOST_USER", None)
    if admin_copy:
        recipients.append(admin_copy)

    recipients = list(dict.fromkeys(recipients))
    return recipients


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_booking_approved_email(self, booking_id: int):
    booking = (
        Booking.objects
        .select_related("tenant", "listing", "listing__owner", "decided_by")
        .get(id=booking_id)
    )

    subject = f"Бронь подтверждена (ID {booking.id})"
    msg = (
        f"Бронь подтверждена.\n\n"
        f"Объявление: {booking.listing.title}\n"
        f"Арендатор: {booking.tenant.email}\n"
        f"Дата заезда: {booking.date_from}\n"
        f"Дата выезда: {booking.date_to}\n"
        f"Статус: {booking.status}\n"
    )

    recipients = _recipients_with_admin_copy(booking)
    if not recipients:
        return {"ok": False, "reason": "no_recipients"}

    send_mail(subject, msg, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
    return {"ok": True, "recipients": recipients}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_booking_canceled_email(self, booking_id: int, canceled_by_user_id: int):
    booking = (
        Booking.objects
        .select_related("tenant", "listing", "listing__owner")
        .get(id=booking_id)
    )

    canceled_by = "арендатором" if booking.tenant_id == canceled_by_user_id else "арендодателем"

    subject = f"Бронь отменена (ID {booking.id})"
    msg = (
        f"Бронь отменена {canceled_by}.\n\n"
        f"Объявление: {booking.listing.title}\n"
        f"Арендатор: {booking.tenant.email}\n"
        f"Дата заезда: {booking.date_from}\n"
        f"Дата выезда: {booking.date_to}\n"
        f"Статус: {booking.status}\n"
    )

    recipients = _recipients_with_admin_copy(booking)
    if not recipients:
        return {"ok": False, "reason": "no_recipients"}

    send_mail(subject, msg, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
    return {"ok": True, "recipients": recipients}