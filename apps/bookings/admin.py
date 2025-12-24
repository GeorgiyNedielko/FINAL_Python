from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "tenant", "date_from", "date_to", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("listing__title", "tenant__email")
    ordering = ("-created_at",)

@admin.action(description="Заблокировать пользователей")
def block_users(self, request, queryset):
    queryset.update(is_active=False)

@admin.action(description="Разблокировать пользователей")
def unblock_users(self, request, queryset):
    queryset.update(is_active=True)

class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "is_active", "is_staff")
    actions = [block_users, unblock_users]
