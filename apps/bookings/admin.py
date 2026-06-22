from django.contrib import admin
from .models import Booking, Payment


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "tenant", "date_from", "date_to", "guests", "total_price", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("listing__title", "tenant__email")
    ordering = ("-created_at",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "amount", "status", "paid_at", "transaction_id")
    list_filter = ("status",)
