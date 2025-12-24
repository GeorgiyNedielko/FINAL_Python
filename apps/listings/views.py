from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from django.db import transaction

from .models import Listing
from .serializers import ListingSerializer
from .permissions import IsLandlord, IsOwnerOrReadOnly

from .tasks import track_listing_view


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer

    # Дает автоматически endpoints:
       # GET / listings / — список
    #    # GET / listings / < id > / — одно    # объявление
    #     # POST / listings / — создать
    #     # PUT / PATCH / listings / < id > / — изменить
    #     # DELETE / listings / < id > / — удалить

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    # django.db.utils.IntegrityError: (1048, "Column 'owner_id' cannot be null")
    # [17 / Dec / 2025 10: 50:26] "POST /api/listings/ HTTP/1.1" 500 295302

    def get_permissions(self):
        if self.action in ("create",):
            return [permissions.IsAuthenticated(), IsLandlord()]
        if self.action in ("update", "partial_update", "destroy", "copy"):
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        return [permissions.AllowAny()]

    @action(detail=True, methods=["post"])
    def copy(self, request, pk=None):
        original = self.get_object()

        with transaction.atomic():
            original.pk = None
            original.id = None
            original.title = f"{original.title} (copy)"
            original.owner = request.user
            original.save()

        return Response(self.get_serializer(original).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()

        user_id = request.user.id if request.user.is_authenticated else None
        track_listing_view.delay(obj.id, user_id, obj.owner_id)

        serializer = self.get_serializer(obj)
        return Response(serializer.data)


def _to_int(v):
    try:
        return int(v)
    except (TypeError,ValueError):
        return None

def _to_decimal(v):
    try:
        return Decimal(v)
    except (TypeError, ValueError, InvalidOperation):
        return None

@require_GET
def listings_search(request):
    """
      GET /api/listings/
      Поиск:
        - q: ключевые слова (title, description)
      Фильтры:
        - price_min, price_max
        - city
        - street/postal_code
        - rooms_min, rooms_max
        - housing_type (apartment/house/room)
      Сортировка:
        - sort=price_asc | price_desc | date_new | date_old
      Пагинация:
        - page, page_size
      """
    qs = Listing.objects.filter(is_active=True)
    warnings = []

    q = request.GET.get("q")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    country = request.GET.get("country")
    if country:
        qs = qs.filter(country__icontains=country)

    #i → insensitive (регистронезависимый),contains → содержит

    district = request.GET.get("district")
    if district:
        qs = qs.filter(Q(street__icontains=district) | Q(postal_code__icontains=district))

    housing_type = request.GET.get("housing_type")
    if housing_type:
        qs = qs.filter(housing_type=housing_type)

    rooms_min = _to_int(request.GET.get("rooms_min"))
    if rooms_min is not None:
        qs = qs.filter(rooms__gte=rooms_min)

    rooms_max = _to_int(request.GET.get("rooms_max"))
    if rooms_max is not None:
        qs = qs.filter(rooms__lte=rooms_max)

    currency = request.GET.get("currency")
    if currency:
        qs = qs.filter(currency=currency)

    price_min = _to_decimal(request.GET.get("price_min"))
    price_max = _to_decimal(request.GET.get("price_max"))

    if (price_min is not None or price_max is not None) and not currency:
        warnings.append(
            "Вы используете price_min/price_max без currency. Сравнение будет выполнено по числам во всех валютах сразу.")

    if price_min is not None:
        qs = qs.filter(price__gte=price_min)
    if price_max is not None:
        qs = qs.filter(price__lte=price_max)

    sort = request.GET.get("sort", "date_new")
    if sort == "price_asc":
        qs = qs.order_by("price", "-created_at")
    elif sort == "price_desc":
        qs = qs.order_by("-price", "-created_at")
    elif sort == "date_old":
        qs = qs.order_by("created_at")
    else:
        qs = qs.order_by("-created_at")

    page = _to_int(request.GET.get("page")) or 1
    page_size = _to_int(request.GET.get("page_size")) or 10
    page_size = max(1, min(page_size, 100))

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    results = []
    for x in page_obj.object_list:
        results.append({
            "id": x.id,
            "title": x.title,
            "description": x.description,
            "price": str(x.price),
            "currency": x.currency,
            "rooms": x.rooms,
            "housing_type": x.housing_type,
            "parking_type": x.parking_type,
            "country": x.country,
            "city": x.city,
            "postal_code": x.postal_code,
            "street": x.street,
            "house_number": x.house_number,
            "floor": x.floor,
            "apartment_number": x.apartment_number,
            "full_address": x.full_address(),
            "created_at": x.created_at.isoformat() if x.created_at else None,
        })

    return JsonResponse({
        "count": paginator.count,
        "pages": paginator.num_pages,
        "page": page_obj.number,
        "page_size": page_size,
        "warnings": warnings,
        "results": results,
    }, json_dumps_params={"ensure_ascii": False})



