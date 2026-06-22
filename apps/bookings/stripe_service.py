"""Stripe Checkout integration for booking payments."""

from __future__ import annotations

import logging
from decimal import Decimal

import stripe
from django.conf import settings
from django.utils import timezone

from .models import Payment

logger = logging.getLogger(__name__)

# ISO 4217 codes supported by our listings mapped to Stripe currency codes (lowercase).
_STRIPE_CURRENCIES = {
    "USD", "EUR", "GBP", "RUB", "UAH", "PLN", "CZK", "CHF", "SEK", "NOK", "DKK",
}


def stripe_enabled() -> bool:
    return bool(getattr(settings, "STRIPE_SECRET_KEY", ""))


def _configure_stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY


def amount_to_stripe_cents(amount: Decimal, currency: str) -> int:
    code = currency.upper()
    if code not in _STRIPE_CURRENCIES:
        raise ValueError(f"Валюта {currency} не поддерживается для Stripe в этом проекте.")
    return int(amount * 100)


def create_checkout_session(*, booking, payment: Payment, request) -> str:
    """Returns Stripe Checkout redirect URL."""
    _configure_stripe()
    listing = booking.listing
    currency = listing.currency.lower()
    unit_amount = amount_to_stripe_cents(payment.amount, listing.currency)

    success_url = request.build_absolute_uri(
        f"/bookings/{booking.pk}/pay/success/?session_id={{CHECKOUT_SESSION_ID}}"
    )
    cancel_url = request.build_absolute_uri(f"/bookings/{booking.pk}/pay/")

    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=booking.tenant.email,
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "unit_amount": unit_amount,
                    "product_data": {
                        "name": listing.title,
                        "description": (
                            f"Бронирование #{booking.id}: "
                            f"{booking.date_from} — {booking.date_to} ({booking.nights} ночей)"
                        ),
                    },
                },
                "quantity": 1,
            }
        ],
        metadata={
            "booking_id": str(booking.id),
            "payment_id": str(payment.id),
        },
        success_url=success_url,
        cancel_url=cancel_url,
    )

    payment.transaction_id = session.id
    payment.save(update_fields=["transaction_id"])
    return session.url


def mark_payment_paid(payment: Payment, transaction_id: str):
    if payment.status == Payment.Status.PAID:
        return
    payment.status = Payment.Status.PAID
    payment.paid_at = timezone.now()
    payment.transaction_id = transaction_id or payment.transaction_id
    payment.save(update_fields=["status", "paid_at", "transaction_id"])


def fulfill_checkout_session(session_id: str) -> Payment | None:
    _configure_stripe()
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status != "paid":
        return None

    payment_id = session.metadata.get("payment_id")
    if not payment_id:
        return None

    payment = Payment.objects.select_related("booking").filter(pk=payment_id).first()
    if not payment:
        return None

    txn = session.payment_intent or session.id
    mark_payment_paid(payment, str(txn))
    return payment


def handle_webhook(payload: bytes, sig_header: str) -> bool:
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.warning("Stripe webhook received but STRIPE_WEBHOOK_SECRET is not set")
        return False

    _configure_stripe()
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return False

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        fulfill_checkout_session(session["id"])
    return True
