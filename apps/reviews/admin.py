from django.contrib import admin
from .models import Review, TenantReview


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "author", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("author__email", "listing__id")
    autocomplete_fields = ("listing", "author", "booking")


@admin.register(TenantReview)
class TenantReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "author", "booking", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("tenant__email", "author__email", "booking__id")
    autocomplete_fields = ("tenant", "author", "booking")
