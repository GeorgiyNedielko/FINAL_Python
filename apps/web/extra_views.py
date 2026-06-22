from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.db import models
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from apps.bookings.models import Booking
from apps.listings.models import Listing
from apps.messaging.models import Conversation, Message
from apps.reviews.models import TenantReview

from .forms import MessageForm, TenantReviewForm


class CustomPasswordResetView(PasswordResetView):
    template_name = "web/auth/password_reset.html"
    email_template_name = "web/auth/password_reset_email.txt"
    subject_template_name = "web/auth/password_reset_subject.txt"
    success_url = reverse_lazy("web:password_reset_done")


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "web/auth/password_reset_done.html"


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "web/auth/password_reset_confirm.html"
    success_url = reverse_lazy("web:password_reset_complete")


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "web/auth/password_reset_complete.html"


@login_required
def inbox(request):
    conversations = (
        Conversation.objects.filter(
            models.Q(tenant=request.user) | models.Q(listing__owner=request.user)
        )
        .select_related("listing", "tenant", "listing__owner")
        .order_by("-updated_at")
    )
    return render(request, "web/messaging/inbox.html", {"conversations": conversations})


@login_required
def conversation_detail(request, pk):
    conv = get_object_or_404(
        Conversation.objects.select_related("listing", "tenant", "listing__owner"),
        pk=pk,
    )
    if request.user.id not in (conv.tenant_id, conv.listing.owner_id):
        return HttpResponseForbidden("Нет доступа")

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                conversation=conv,
                sender=request.user,
                body=form.cleaned_data["body"],
            )
            conv.save(update_fields=["updated_at"])
            return redirect("web:conversation", pk=pk)
    else:
        form = MessageForm()

    chat_messages = conv.messages.select_related("sender").order_by("created_at")
    conv.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    return render(
        request,
        "web/messaging/conversation.html",
        {"conversation": conv, "chat_messages": chat_messages, "form": form},
    )


@login_required
def start_conversation(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id, is_active=True)
    if listing.owner_id == request.user.id:
        messages.error(request, "Нельзя написать самому себе.")
        return redirect("web:listing_detail", pk=listing_id)

    conv, _ = Conversation.objects.get_or_create(listing=listing, tenant=request.user)
    return redirect("web:conversation", pk=conv.pk)


@login_required
def create_tenant_review(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("listing"), pk=pk)
    if booking.listing.owner_id != request.user.id:
        return HttpResponseForbidden("Нет доступа")
    if booking.status not in (Booking.Status.APPROVED, Booking.Status.COMPLETED):
        messages.error(request, "Отзыв о госте доступен после подтверждённой брони.")
        return redirect("web:booking_detail", pk=pk)
    if hasattr(booking, "tenant_review"):
        messages.error(request, "Отзыв уже оставлен.")
        return redirect("web:booking_detail", pk=pk)

    form = TenantReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        TenantReview.objects.create(
            booking=booking,
            tenant_id=booking.tenant_id,
            author=request.user,
            rating=form.cleaned_data["rating"],
            text=form.cleaned_data["text"],
        )
        messages.success(request, "Отзыв о госте сохранён.")
    return redirect("web:booking_detail", pk=pk)
