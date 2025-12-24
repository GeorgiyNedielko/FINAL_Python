from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import get_user_model

from .models import UserBlock

User = get_user_model()


@admin.action(description="Заблокировать пользователей")
def block_users(modeladmin, request, queryset):
    created_count = 0

    for user in queryset:
        block, created = UserBlock.objects.get_or_create(
            user=user,
            defaults={"reason": "Заблокирован администратором"},
        )
        if created:
            created_count += 1

        if user.is_active:
            user.is_active = False
            user.save(update_fields=["is_active"])

    modeladmin.message_user(
        request,
        f"Заблокировано: {queryset.count()} (новых записей UserBlock: {created_count})",
        level=messages.SUCCESS,
    )


@admin.action(description="Разблокировать пользователей")
def unblock_users(modeladmin, request, queryset):
    deleted, _ = UserBlock.objects.filter(user__in=queryset).delete()
    updated = queryset.update(is_active=True)

    modeladmin.message_user(
        request,
        f"Разблокировано пользователей: {updated}. Удалено записей UserBlock: {deleted}.",
        level=messages.SUCCESS,
    )


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User

    list_display = ("id", "email", "username", "role", "is_staff", "is_active")
    list_display_links = ("email", "username")
    list_filter = ("role", "is_staff", "is_active")
    actions = [block_users, unblock_users]

    ordering = ("email",)
    search_fields = ("email", "username")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username", "first_name", "last_name")}),
        ("Role", {"fields": ("role",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "role", "password1", "password2", "is_staff", "is_superuser"),
        }),
    )


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ("user", "blocked_at", "reason")
    search_fields = ("user__email",)
    autocomplete_fields = ("user",)
