from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.bookings.models import Booking, Payment
from apps.bookings.stripe_service import (
    create_checkout_session,
    fulfill_checkout_session,
    handle_webhook,
    stripe_enabled,
)
from apps.listings.services import (
    base_listing_queryset,
    filter_listings,
    get_booked_date_ranges,
    similar_listings,
)
from apps.bookings.tasks import (
    send_booking_approved_email,
    send_booking_canceled_email,
    send_booking_created_email,
    send_payment_received_email,
)
from apps.reviews.models import Review, TenantReview
from apps.listings.models import Amenity, Favorite, Listing, ListingImage
from apps.listings.tasks import save_listing_view_event, track_listing_view
from apps.users.models import User

from .forms import (
    BookingForm,
    EmailAuthenticationForm,
    ListingForm,
    RegisterForm,
    ReviewForm,
    SearchForm,
    TenantReviewForm,
)
from .utils import (
    check_login_rate_limit,
    clear_login_failures,
    record_login_failure,
    validate_uploaded_images,
)


class HomeView(TemplateView):
    template_name = "web/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = SearchForm(self.request.GET or None)
        ctx["popular_listings"] = base_listing_queryset().order_by("-reviews_count")[:8]
        ctx["amenities"] = Amenity.objects.all()[:12]
        return ctx


class ListingSearchView(ListView):
    template_name = "web/listings/search.html"
    context_object_name = "listings"
    paginate_by = 12

    def get_queryset(self):
        qs = base_listing_queryset()
        return filter_listings(qs, self.request.GET, user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = SearchForm(self.request.GET)
        ctx["amenities"] = Amenity.objects.all()
        ctx["housing_types"] = Listing.HousingType.choices
        return ctx


class ListingDetailView(DetailView):
    model = Listing
    template_name = "web/listings/detail.html"
    context_object_name = "listing"

    def get_queryset(self):
        return base_listing_queryset()

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        user_id = user.id if user.is_authenticated else None
        try:
            track_listing_view.delay(obj.id, user_id, obj.owner_id)
            if user.is_authenticated:
                save_listing_view_event.delay(obj.id, user.id)
        except Exception:
            pass
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        listing = self.object
        ctx["reviews"] = listing.reviews.select_related("author").order_by("-created_at")[:20]
        ctx["booking_form"] = BookingForm(
            self.request.GET or None,
            listing=listing,
            initial={"guests": self.request.GET.get("guests") or 2},
        )
        ctx["is_favorite"] = False
        if self.request.user.is_authenticated:
            ctx["is_favorite"] = Favorite.objects.filter(
                user=self.request.user, listing=listing
            ).exists()
        ctx["maps_url"] = (
            f"https://www.google.com/maps/search/?api=1&query={listing.full_address()}"
        )
        if listing.latitude and listing.longitude:
            ctx["maps_embed_url"] = (
                f"https://maps.google.com/maps?q={listing.latitude},{listing.longitude}&z=15&output=embed"
            )
        ctx["booked_ranges"] = get_booked_date_ranges(listing.pk)
        ctx["similar_listings"] = similar_listings(listing)
        return ctx


class RegisterView(View):
    template_name = "web/auth/register.html"

    def get(self, request):
        return render(request, self.template_name, {"form": RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Добро пожаловать! Аккаунт создан.")
            return redirect("web:home")
        return render(request, self.template_name, {"form": form})


class LoginView(View):
    template_name = "web/auth/login.html"

    def get(self, request):
        return render(request, self.template_name, {"form": EmailAuthenticationForm()})

    def post(self, request):
        email = request.POST.get("username", "")
        if not check_login_rate_limit(request, email):
            messages.error(request, "Слишком много попыток. Подождите 15 минут.")
            return render(request, self.template_name, {"form": EmailAuthenticationForm()})

        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            clear_login_failures(request, email)
            login(request, form.get_user())
            messages.success(request, "Вы вошли в аккаунт.")
            next_url = request.GET.get("next") or reverse("web:home")
            return redirect(next_url)

        if "заблокирован" in str(form.errors).lower() or "inactive" in str(form.errors).lower():
            messages.error(request, "Аккаунт заблокирован. Обратитесь в поддержку.")
        else:
            record_login_failure(request, email)
        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        messages.info(request, "Вы вышли из аккаунта.")
        return redirect("web:home")


class LandlordRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == User.Role.LANDLORD


class ListingCreateView(LoginRequiredMixin, LandlordRequiredMixin, CreateView):
    model = Listing
    form_class = ListingForm
    template_name = "web/listings/form.html"

    def get_success_url(self):
        return reverse("web:listing_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        self._save_images()
        messages.success(self.request, "Объявление опубликовано.")
        return response

    def _save_images(self):
        files = self.request.FILES.getlist("images")
        if not files:
            return
        try:
            validate_uploaded_images(files)
        except Exception as exc:
            messages.warning(self.request, str(exc))
            return
        for i, f in enumerate(files):
            ListingImage.objects.create(
                listing=self.object,
                image=f,
                is_primary=(i == 0 and not self.object.images.exists()),
                order=self.object.images.count() + i,
            )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Новое объявление"
        return ctx


class ListingUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Listing
    form_class = ListingForm
    template_name = "web/listings/form.html"

    def get_success_url(self):
        return reverse("web:listing_detail", kwargs={"pk": self.object.pk})

    def test_func(self):
        listing = self.get_object()
        return self.request.user.id == listing.owner_id

    def form_valid(self, form):
        response = super().form_valid(form)
        files = self.request.FILES.getlist("images")
        if files:
            has_primary = self.object.images.filter(is_primary=True).exists()
            for i, f in enumerate(files):
                ListingImage.objects.create(
                    listing=self.object,
                    image=f,
                    is_primary=(not has_primary and i == 0),
                    order=self.object.images.count() + i,
                )
        messages.success(self.request, "Объявление обновлено.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Редактирование объявления"
        return ctx


@login_required
def listing_delete(request, pk):
    listing = get_object_or_404(Listing, pk=pk, owner=request.user)
    if request.method == "POST":
        listing.is_active = False
        listing.save(update_fields=["is_active"])
        listing.delete()
        messages.info(request, "Объявление снято с публикации.")
        return redirect("web:my_listings")
    return render(request, "web/listings/confirm_delete.html", {"listing": listing})


@login_required
def create_booking(request, pk):
    listing = get_object_or_404(base_listing_queryset(), pk=pk)
    if listing.owner_id == request.user.id:
        messages.error(request, "Нельзя бронировать своё жильё.")
        return redirect("web:listing_detail", pk=pk)

    form = BookingForm(request.POST, listing=listing)
    if not form.is_valid():
        messages.error(request, " ".join(form.errors.get("__all__", ["Проверьте даты бронирования."])))
        return redirect(f"{reverse('web:listing_detail', kwargs={'pk': pk})}?{request.POST.urlencode()}")

    booking = form.save(commit=False)
    booking.listing = listing
    booking.tenant = request.user
    if listing.instant_book:
        booking.status = Booking.Status.APPROVED
        booking.decided_at = timezone.now()
        booking.decided_by = listing.owner
    else:
        booking.status = Booking.Status.PENDING
    booking.recalculate_total()
    booking.save()

    Payment.objects.get_or_create(
        booking=booking,
        defaults={"amount": booking.total_price, "status": Payment.Status.PENDING},
    )

    if listing.instant_book:
        try:
            send_booking_approved_email.delay(booking.id)
        except Exception:
            send_booking_approved_email.run(booking.id)
        messages.success(request, "Бронирование подтверждено автоматически! Перейдите к оплате.")
    else:
        try:
            send_booking_created_email.delay(booking.id)
        except Exception:
            send_booking_created_email.run(booking.id)
        messages.success(request, "Заявка отправлена. Ожидайте подтверждения хозяина.")
    return redirect("web:booking_detail", pk=booking.pk)


@login_required
def my_bookings(request):
    qs = (
        Booking.objects.filter(
            Q(tenant=request.user) | Q(listing__owner=request.user)
        )
        .select_related("listing", "tenant", "listing__owner", "payment")
        .order_by("-created_at")
    )
    return render(request, "web/account/bookings.html", {"bookings": qs})


@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("listing", "tenant", "payment"),
        pk=pk,
    )
    if booking.tenant_id != request.user.id and booking.listing.owner_id != request.user.id:
        return HttpResponseForbidden("Нет доступа")

    try:
        review = booking.review
    except Review.DoesNotExist:
        review = None

    tenant_review = None
    try:
        tenant_review = booking.tenant_review
    except TenantReview.DoesNotExist:
        pass

    return render(
        request,
        "web/booking/detail.html",
        {
            "booking": booking,
            "review": review,
            "tenant_review": tenant_review,
            "review_form": ReviewForm(),
            "tenant_review_form": TenantReviewForm(),
        },
    )


@login_required
def booking_approve(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("listing"), pk=pk)
    if booking.listing.owner_id != request.user.id:
        return HttpResponseForbidden("Нет доступа")
    if booking.status != Booking.Status.PENDING:
        messages.error(request, "Можно подтверждать только ожидающие брони.")
        return redirect("web:booking_detail", pk=pk)

    overlap = Booking.objects.filter(
        listing_id=booking.listing_id,
        status=Booking.Status.APPROVED,
        date_from__lt=booking.date_to,
        date_to__gt=booking.date_from,
    ).exclude(id=booking.id).exists()
    if overlap:
        messages.error(request, "Даты пересекаются с другим подтверждённым бронированием.")
        return redirect("web:booking_detail", pk=pk)

    booking.status = Booking.Status.APPROVED
    booking.decided_at = timezone.now()
    booking.decided_by = request.user
    booking.save()

    Payment.objects.update_or_create(
        booking=booking,
        defaults={"amount": booking.total_price, "status": Payment.Status.PENDING},
    )

    try:
        send_booking_approved_email.delay(booking.id)
    except Exception:
        send_booking_approved_email.run(booking.id)

    messages.success(request, "Бронирование подтверждено. Ожидается оплата.")
    return redirect("web:booking_detail", pk=pk)


@login_required
def booking_reject(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("listing"), pk=pk)
    if booking.listing.owner_id != request.user.id:
        return HttpResponseForbidden("Нет доступа")
    if booking.status != Booking.Status.PENDING:
        messages.error(request, "Можно отклонять только ожидающие брони.")
        return redirect("web:booking_detail", pk=pk)

    booking.status = Booking.Status.REJECTED
    booking.decided_at = timezone.now()
    booking.decided_by = request.user
    booking.save()
    messages.info(request, "Бронирование отклонено.")
    return redirect("web:my_bookings")


@login_required
def booking_cancel(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("listing"), pk=pk)
    user = request.user
    if booking.tenant_id != user.id and booking.listing.owner_id != user.id and not user.is_staff:
        return HttpResponseForbidden("Нет доступа")
    if not booking.can_cancel():
        messages.error(request, "Это бронирование нельзя отменить.")
        return redirect("web:booking_detail", pk=pk)

    booking.status = Booking.Status.CANCELED
    booking.canceled_at = timezone.now()
    booking.save()

    if hasattr(booking, "payment") and booking.payment.status == Payment.Status.PAID:
        booking.payment.status = Payment.Status.REFUNDED
        booking.payment.save(update_fields=["status"])

    try:
        send_booking_canceled_email.delay(booking.id, user.id)
    except Exception:
        send_booking_canceled_email.run(booking.id, user.id)

    messages.info(request, "Бронирование отменено.")
    return redirect("web:my_bookings")


@login_required
def booking_pay(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("listing", "payment"),
        pk=pk,
        tenant=request.user,
    )
    if booking.status != Booking.Status.APPROVED:
        messages.error(request, "Оплата доступна только для подтверждённых броней.")
        return redirect("web:booking_detail", pk=pk)

    payment, _ = Payment.objects.get_or_create(
        booking=booking,
        defaults={"amount": booking.total_price, "status": Payment.Status.PENDING},
    )

    if payment.status == Payment.Status.PAID:
        messages.info(request, "Бронирование уже оплачено.")
        return redirect("web:booking_detail", pk=pk)

    if request.method == "POST":
        if stripe_enabled():
            try:
                checkout_url = create_checkout_session(
                    booking=booking, payment=payment, request=request
                )
                return redirect(checkout_url)
            except Exception as exc:
                messages.error(request, f"Ошибка Stripe: {exc}")
                return redirect("web:booking_detail", pk=pk)

        payment.status = Payment.Status.PAID
        payment.paid_at = timezone.now()
        payment.transaction_id = f"MOCK-{booking.id}-{int(timezone.now().timestamp())}"
        payment.save()
        try:
            send_payment_received_email.delay(booking.id)
        except Exception:
            send_payment_received_email.run(booking.id)
        messages.success(request, "Оплата прошла успешно (демо-режим).")
        return redirect("web:booking_detail", pk=pk)

    return render(
        request,
        "web/booking/payment.html",
        {
            "booking": booking,
            "payment": payment,
            "stripe_enabled": stripe_enabled(),
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        },
    )


@login_required
def booking_pay_success(request, pk):
    booking = get_object_or_404(Booking, pk=pk, tenant=request.user)
    session_id = request.GET.get("session_id")

    if stripe_enabled() and session_id:
        try:
            payment = fulfill_checkout_session(session_id)
            if payment and payment.booking_id == booking.id:
                try:
                    send_payment_received_email.delay(booking.id)
                except Exception:
                    send_payment_received_email.run(booking.id)
                messages.success(request, "Оплата через Stripe прошла успешно!")
                return redirect("web:booking_detail", pk=pk)
        except Exception as exc:
            messages.error(request, f"Не удалось подтвердить оплату: {exc}")
            return redirect("web:booking_detail", pk=pk)

    messages.warning(request, "Ожидаем подтверждение оплаты. Обновите страницу брони через минуту.")
    return redirect("web:booking_detail", pk=pk)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    if not handle_webhook(request.body, sig):
        return HttpResponseForbidden("Invalid signature")
    return HttpResponse(status=200)


@login_required
def create_review(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("listing"), pk=pk)
    if booking.tenant_id != request.user.id:
        return HttpResponseForbidden("Нет доступа")
    if booking.status not in (Booking.Status.APPROVED, Booking.Status.COMPLETED):
        messages.error(request, "Отзыв можно оставить после подтверждённого проживания.")
        return redirect("web:booking_detail", pk=pk)

    if hasattr(booking, "review"):
        messages.error(request, "Отзыв уже оставлен.")
        return redirect("web:booking_detail", pk=pk)

    form = ReviewForm(request.POST)
    if form.is_valid():
        Review.objects.create(
            listing=booking.listing,
            booking=booking,
            author=request.user,
            rating=form.cleaned_data["rating"],
            text=form.cleaned_data["text"],
        )
        messages.success(request, "Спасибо за отзыв!")
    else:
        messages.error(request, "Проверьте оценку и текст отзыва.")
    return redirect("web:booking_detail", pk=pk)


@login_required
def my_listings(request):
    listings = (
        Listing.all_objects.filter(owner=request.user, is_deleted=False)
        .prefetch_related("images")
        .annotate(
            avg_rating=Coalesce(Avg("reviews__rating"), 0.0),
            reviews_count=Count("reviews", distinct=True),
        )
        .order_by("-created_at")
    )
    return render(request, "web/account/listings.html", {"listings": listings})


@login_required
def favorites(request):
    listing_ids = Favorite.objects.filter(user=request.user).values_list("listing_id", flat=True)
    listings = (
        base_listing_queryset()
        .filter(id__in=listing_ids)
        .order_by("-created_at")
    )
    return render(request, "web/account/favorites.html", {"listings": listings})


@login_required
def toggle_favorite(request, pk):
    listing = get_object_or_404(Listing, pk=pk, is_active=True)
    fav, created = Favorite.objects.get_or_create(user=request.user, listing=listing)
    if not created:
        fav.delete()
        messages.info(request, "Удалено из избранного.")
    else:
        messages.success(request, "Добавлено в избранное.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("web:listing_detail", kwargs={"pk": pk}))


@login_required
def profile(request):
    return render(request, "web/account/profile.html", {"user_obj": request.user})
