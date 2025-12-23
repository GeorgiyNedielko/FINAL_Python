from rest_framework.permissions import BasePermission
from .models import Booking


class IsTenant(BasePermission):
    def has_object_permission(self, request, view, obj: Booking):
        return obj.tenant_id == request.user.id


class IsListingOwner(BasePermission):
    def has_object_permission(self, request, view, obj: Booking):
        return obj.listing.owner_id == request.user.id
