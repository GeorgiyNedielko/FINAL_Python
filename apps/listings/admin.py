from urllib.parse import quote_plus

from django.conf import settings
from django.contrib import admin
from django.db.models import OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce
from django.utils.html import format_html

from rangefilter.filters import DateTimeRangeFilter

from .models import Listing, ListingViewStat


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
        "views_total_admin",
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

    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    actions = ["restore_selected", "hard_delete_selected", "copy_listing"]
    list_select_related = ("owner",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)


        subq = ListingViewStat.objects.filter(
            listing_id=OuterRef("pk")
        ).values("views_total")[:1]

        qs = qs.annotate(
            _views_total=Coalesce(Subquery(subq, output_field=IntegerField()), Value(0))
        )

        # твоя логика soft-delete
        if hasattr(Listing, "is_deleted"):
            qs = qs.filter(is_deleted=False)

        return qs

    @admin.display(description="Views", ordering="_views_total")
    def views_total_admin(self, obj: Listing):
        return getattr(obj, "_views_total", 0)

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
        url = settings.MAPS_SEARCH_URL + quote_plus(address)
        return format_html('<a href="{}" target="_blank">Открыть</a>', url)

    @admin.action(description="Скопировать объявление")
    def copy_listing(self, request, queryset):
        for obj in queryset:
            obj.pk = None
            obj.id = None
            obj.save()


@admin.register(ListingViewStat)
class ListingViewStatAdmin(admin.ModelAdmin):
    list_display = (
        "listing_id",
        "views_total",
        "updated_at",
    )
    search_fields = (
        "listing__id",
        "listing__title",
        "listing__owner__email",
    )
    ordering = ("-views_total",)
    list_select_related = ("listing",)

