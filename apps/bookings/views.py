from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Booking
from .permissions import IsTenant, IsListingOwner
from .serializers import BookingCreateSerializer, BookingSerializer

from .tasks import send_booking_created_email
from .tasks import send_booking_created_email, send_booking_approved_email, send_booking_canceled_email

class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Booking.objects.select_related("listing", "tenant", "decided_by")

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user


        return qs.filter(tenant=user) | qs.filter(listing__owner=user)


    @action(methods=["post"], detail=True, permission_classes=[IsAuthenticated, IsTenant])
    def cancel(self, request, pk=None):
        booking: Booking = self.get_object()

        user_id = request.user.id
        is_tenant = booking.tenant_id == user_id
        is_owner = booking.listing.owner_id == user_id
        is_admin = request.user.is_staff or request.user.is_superuser

        if not (is_tenant or is_owner or is_admin):
            return Response({"detail": "Нет доступа."}, status=403)

        if not booking.can_cancel():
            return Response({"detail": "Нельзя отменить это бронирование."}, status=400)

        booking.status = Booking.Status.CANCELED
        booking.canceled_at = timezone.now()


        booking.save(update_fields=["status", "canceled_at", "updated_at"])
        return Response({"detail": "Отменено."})

    @action(methods=["post"], detail=True, permission_classes=[IsAuthenticated, IsListingOwner])
    def approve(self, request, pk=None):
        booking: Booking = self.get_object()

        if booking.status != Booking.Status.PENDING:
            return Response({"detail": "Можно подтверждать только pending."}, status=400)


        overlap = Booking.objects.filter(
            listing_id=booking.listing_id,
            status=Booking.Status.APPROVED,
            date_from__lt=booking.date_to,
            date_to__gt=booking.date_from,
        ).exclude(id=booking.id).exists()

        if overlap:
            return Response({"detail": "Есть пересечение с уже подтвержденным бронированием."}, status=400)

        booking.status = Booking.Status.APPROVED
        booking.decided_at = timezone.now()
        booking.decided_by = request.user
        booking.save(update_fields=["status", "decided_at", "decided_by", "updated_at"])
        return Response({"detail": "Подтверждено."})

    @action(methods=["post"], detail=True, permission_classes=[IsAuthenticated, IsListingOwner])
    def reject(self, request, pk=None):
        booking: Booking = self.get_object()

        if booking.status != Booking.Status.PENDING:
            return Response({"detail": "Можно отклонять только pending."}, status=400)

        booking.status = Booking.Status.REJECTED
        booking.decided_at = timezone.now()
        booking.decided_by = request.user
        booking.save(update_fields=["status", "decided_at", "decided_by", "updated_at"])
        return Response({"detail": "Отклонено."})

    def perform_create(self, serializer):
        booking = serializer.save()
        send_booking_created_email.delay(booking.id)
        send_booking_canceled_email.delay(booking.id, request.user.id)

