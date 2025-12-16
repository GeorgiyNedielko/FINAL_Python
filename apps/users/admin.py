from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User

    # что видно в списке пользователей
    list_display = ("id", "email", "username", "role", "is_staff", "is_active")
    list_display_links = ("email", "username")
    list_filter = ("role", "is_staff", "is_active")

    ordering = ("email",)
    search_fields = ("email", "username")

    # что видно при редактировании пользователя
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username", "first_name", "last_name")}),
        ("Role", {"fields": ("role",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # что видно при создании нового пользователя
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "role", "password1", "password2", "is_staff", "is_superuser"),
        }),
    )
