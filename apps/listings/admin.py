from django.contrib import admin
from django.utils.html import format_html
from urllib.parse import quote_plus

from rangefilter.filters import DateTimeRangeFilter

from .models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "price_with_currency",
        "housing_type",
        "rooms",
        "parking_type",
        "is_active",
        "owner",
        "maps_link",
        "is_deleted",
        "created_at",
    )


    list_filter = (
        ("created_at", DateTimeRangeFilter),
        "housing_type",
        "parking_type",
        "is_active",
        "is_deleted",
        "currency",
        "city",
    )


    search_fields = (
        "title",
        "description",
        "city",
        "street",
        "postal_code",
        "owner__email",
    )

    ordering = ("-created_at",)

    actions = ["restore_selected", "hard_delete_selected", "copy_listing"]

    list_select_related = ("owner",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if hasattr(Listing, "is_deleted"):
            qs = qs.filter(is_deleted=False)
        return qs

    @admin.action(description="Восстановить выбранные (soft delete → restore)")
    def restore_selected(self, request, queryset):
        for obj in queryset:
            obj.restore()

    @admin.action(description="Удалить НАВСЕГДА (hard delete)")
    def hard_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.hard_delete()

    @admin.display(description="Цена")
    def price_with_currency(self, obj: Listing):
        return f"{obj.price} {obj.currency}"

    @admin.display(description="Карта")
    def maps_link(self, obj: Listing):
        address = obj.full_address()
        if not address:
            return "—"
        url = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(address) # УБРАТЬ ЕНВ
        return format_html('<a href="{}" target="_blank">Открыть</a>', url)

    @admin.action(description="Скопировать объявление")
    def copy_listing(self, request, queryset):
        for obj in queryset:
            obj.pk = None
            obj.id = None
            obj.save()