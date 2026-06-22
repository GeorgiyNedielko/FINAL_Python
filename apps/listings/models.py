from django.conf import settings
from django.db import models
from decimal import Decimal
from apps.common.models import SoftDeleteModel


class Listing(SoftDeleteModel):
    class HousingType(models.TextChoices):
        APARTMENT = "apartment", "Квартира"
        HOUSE = "house", "Дом"
        ROOM = "room", "Комната"

    class ParkingType(models.TextChoices):
        NONE = "none", "Нет"
        PARKING_SPACE = "parking_space", "Паркоместо"
        GARAGE = "garage", "Гараж"

    class Currency(models.TextChoices):
        USD = "USD", "USD"
        EUR = "EUR", "EUR"
        RUB = "RUB", "RUB"
        UAH = "UAH", "UAH"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE,
                              related_name="listings",
                              verbose_name="Владелец",)

    title = models.CharField(max_length=255, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")

    country = models.CharField(max_length=100, blank=True, default="", verbose_name="Страна")
    city = models.CharField(max_length=100, blank=True, default="", verbose_name="Город")
    postal_code = models.CharField(max_length=20, blank=True, default="", verbose_name="Индекс")
    street = models.CharField(max_length=255, blank=True, default="", verbose_name="Улица")
    house_number = models.CharField(max_length=20, blank=True, default="", verbose_name="Дом")
    floor = models.CharField(max_length=20, blank=True, default="", verbose_name="Этаж")
    apartment_number = models.CharField(max_length=20, blank=True, default="", verbose_name="Квартира")



    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена за ночь",
    )

    max_guests = models.PositiveSmallIntegerField(default=2, verbose_name="Макс. гостей")
    beds = models.PositiveSmallIntegerField(default=1, verbose_name="Кроватей")
    bathrooms = models.PositiveSmallIntegerField(default=1, verbose_name="Ванных")

    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
        verbose_name="Валюта"
    )

    rooms = models.PositiveSmallIntegerField(verbose_name="Количество комнат")

    housing_type = models.CharField(
        max_length=20,
        choices=HousingType.choices,
        verbose_name="Тип жилья",
    )

    parking_type = models.CharField(
        max_length=20,
        choices=ParkingType.choices,
        default=ParkingType.NONE,
        verbose_name="Парковка",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    instant_book = models.BooleanField(default=False, verbose_name="Мгновенное бронирование")
    min_nights = models.PositiveSmallIntegerField(default=1, verbose_name="Мин. ночей")
    platform_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Комиссия платформы (%)",
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Широта"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Долгота"
    )

    amenities = models.ManyToManyField(
        "Amenity",
        blank=True,
        related_name="listings",
        verbose_name="Удобства",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} — {self.price}"



    def full_address(self) -> str:

        parts = [
            self.country,
            self.city,
            self.postal_code,
            self.street,
            self.house_number,
        ]
        base = ", ".join([p for p in parts if p])

        extra = []
        if self.floor:
            extra.append(f"этаж {self.floor}")
        if self.apartment_number:
            extra.append(f"кв. {self.apartment_number}")

        if extra and base:
            return f"{base}, " + ", ".join(extra)
        return base or ", ".join(extra) or ""

    def price_for_stay(self, date_from, date_to):
        nights = (date_to - date_from).days
        if nights < 1:
            return Decimal("0")
        subtotal = self.price * nights
        fee_pct = self.platform_fee_percent or Decimal("0")
        if fee_pct > 0:
            subtotal += subtotal * fee_pct / Decimal("100")
        return subtotal.quantize(Decimal("0.01"))

    def is_date_blocked(self, d) -> bool:
        return self.blocked_dates.filter(date=d).exists()

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        if img:
            return img
        return self.images.order_by("order", "id").first()


class ListingBlockedDate(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="blocked_dates",
        verbose_name="Объявление",
    )
    date = models.DateField(verbose_name="Дата")
    reason = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        verbose_name = "Заблокированная дата"
        verbose_name_plural = "Заблокированные даты"
        constraints = [
            models.UniqueConstraint(fields=["listing", "date"], name="unique_listing_blocked_date"),
        ]
        ordering = ["date"]

    def __str__(self):
        return f"{self.listing_id} — {self.date}"


class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название")
    icon = models.CharField(max_length=8, blank=True, default="", verbose_name="Иконка")
    category = models.CharField(max_length=50, blank=True, default="", verbose_name="Категория")

    class Meta:
        verbose_name = "Удобство"
        verbose_name_plural = "Удобства"
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class ListingImage(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Объявление",
    )
    image = models.ImageField(upload_to="listings/%Y/%m/", verbose_name="Фото")
    is_primary = models.BooleanField(default=False, verbose_name="Главное")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Порядок")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Фото объявления"
        verbose_name_plural = "Фото объявлений"
        ordering = ["order", "id"]

    def __str__(self):
        return f"Фото #{self.id} — {self.listing_id}"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        constraints = [
            models.UniqueConstraint(fields=["user", "listing"], name="unique_user_listing_favorite"),
        ]

    def __str__(self):
        return f"{self.user_id} → {self.listing_id}"


class ListingViewStat(models.Model):
    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="view_stat",
        primary_key=True,
    )
    views_total = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.listing_id}: {self.views_total}"

class ListingViewEvent(models.Model):
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="view_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_views",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["listing", "created_at"]),
        ]

    def __str__(self):
        return f"user={self.user_id} listing={self.listing_id}"

class SearchQuery(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="search_queries",
    )
    query = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["query"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["query", "created_at"]),
        ]

    def __str__(self):
        return self.query