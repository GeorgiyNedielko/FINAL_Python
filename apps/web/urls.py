from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("search/", views.ListingSearchView.as_view(), name="search"),
    path("listings/<int:pk>/", views.ListingDetailView.as_view(), name="listing_detail"),
    path("listings/new/", views.ListingCreateView.as_view(), name="listing_create"),
    path("listings/<int:pk>/edit/", views.ListingUpdateView.as_view(), name="listing_edit"),
    path("listings/<int:pk>/delete/", views.listing_delete, name="listing_delete"),
    path("listings/<int:pk>/book/", views.create_booking, name="create_booking"),
    path("listings/<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("account/", views.profile, name="profile"),
    path("account/bookings/", views.my_bookings, name="my_bookings"),
    path("account/listings/", views.my_listings, name="my_listings"),
    path("account/favorites/", views.favorites, name="favorites"),
    path("bookings/<int:pk>/", views.booking_detail, name="booking_detail"),
    path("bookings/<int:pk>/approve/", views.booking_approve, name="booking_approve"),
    path("bookings/<int:pk>/reject/", views.booking_reject, name="booking_reject"),
    path("bookings/<int:pk>/cancel/", views.booking_cancel, name="booking_cancel"),
    path("bookings/<int:pk>/pay/", views.booking_pay, name="booking_pay"),
    path("bookings/<int:pk>/pay/success/", views.booking_pay_success, name="booking_pay_success"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("bookings/<int:pk>/review/", views.create_review, name="create_review"),
]
