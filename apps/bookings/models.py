from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.listings.models import Listing


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает подтверждения"
        APPROVED = "approved", "Подтверждено"
        REJECTED = "rejected", "Отклонено"
        CANCELED = "canceled", "Отменено"
        COMPLETED = "completed", "Завершено"

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="Объявление",
    )

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="Арендатор",
    )

    date_from = models.DateField(verbose_name="Дата заезда")
    date_to = models.DateField(verbose_name="Дата выезда")
    guests = models.PositiveSmallIntegerField(default=1, verbose_name="Гостей")
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Сумма",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
    )

    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bookings_decided",
    )

    canceled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["listing", "status", "date_from", "date_to"]),
            models.Index(fields=["tenant", "status", "date_from"]),
        ]

    def __str__(self):
        return f"Booking #{self.id} listing={self.listing_id} tenant={self.tenant_id} {self.date_from}->{self.date_to} {self.status}"

    def can_cancel(self) -> bool:
        return timezone.localdate() < self.date_from and self.status in {self.Status.PENDING, self.Status.APPROVED}

    @property
    def nights(self) -> int:
        return max((self.date_to - self.date_from).days, 0)

    def recalculate_total(self):
        self.total_price = self.listing.price_for_stay(self.date_from, self.date_to)
        return self.total_price


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает оплаты"
        PAID = "paid", "Оплачено"
        REFUNDED = "refunded", "Возврат"

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="payment",
        verbose_name="Бронирование",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Сумма")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
    )
    transaction_id = models.CharField(max_length=255, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"

    def __str__(self):
        return f"Payment #{self.id} booking={self.booking_id} {self.status}"
