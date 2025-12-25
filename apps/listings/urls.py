from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ListingViewSet

from .views import listings_search

from .views import popular_searches

router = DefaultRouter()
router.register(r"listings", ListingViewSet, basename="listing")

urlpatterns = [
    path("", include(router.urls)),
    path("listings-search/", listings_search, name="listings_search"),
    path("listings/search/popular/", popular_searches),
]
