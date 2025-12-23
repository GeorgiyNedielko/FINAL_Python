from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "tenant", "date_from", "date_to", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("listing__title", "tenant__email")
    ordering = ("-created_at",)
