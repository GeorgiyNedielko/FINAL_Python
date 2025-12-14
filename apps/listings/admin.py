from django.contrib import admin
from django.utils.html import format_html
from urllib.parse import quote_plus

from .models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "price",
        "housing_type",
        "rooms",
        "parking_type",
        "is_active",
        "owner",
        "maps_link",
        "is_deleted",
        "created_at",
    )
    list_filter = ("housing_type", "parking_type", "is_active", "is_deleted")
    search_fields = ("title", "city", "street", "postal_code")

    actions = ["restore_selected", "hard_delete_selected"]

    def get_queryset(self, request):
        return Listing.all_objects.all()

    @admin.action(description="Восстановить выбранные (soft delete -> restore)")
    def restore_selected(self, request, queryset):
        for obj in queryset:
            obj.restore()

    @admin.action(description="Удалить НАВСЕГДА (hard delete)")
    def hard_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.hard_delete()

    @admin.display(description="Карта")
    def maps_link(self, obj: Listing):
        address = obj.full_address()
        if not address:
            return "—"
        url = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(address)
        return format_html('<a href="{}" target="_blank">Открыть</a>', url)
