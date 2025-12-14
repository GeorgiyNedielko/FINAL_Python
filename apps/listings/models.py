
# Create your models here.

from django.conf import settings
from django.db import models
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

    # location = models.CharField(max_length=255, verbose_name="Местоположение")

    class Currency(models.TextChoices):
        USD = "USD", "USD"
        EUR = "EUR", "EUR"
        RUB = "RUB", "RUB"
        UAH = "UAH", "UAH"

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена"
    )

    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
        verbose_name="Валюта"
    )

    # price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена, USD")
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

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} — {self.price}"

    #ПРОБА ГУГЛ + 36(-) location....

    def full_address(self) -> str:
        """
        Собираем адрес одной строкой (для отображения и Google Maps).
        """
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