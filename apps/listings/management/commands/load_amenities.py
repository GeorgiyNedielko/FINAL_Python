from django.core.management.base import BaseCommand

from apps.listings.models import Amenity

DEFAULT_AMENITIES = [
    ("Wi-Fi", "📶", "Интернет"),
    ("Кондиционер", "❄️", "Комфорт"),
    ("Отопление", "🔥", "Комфорт"),
    ("Кухня", "🍳", "Кухня"),
    ("Стиральная машина", "🧺", "Удобства"),
    ("Парковка", "🅿️", "Парковка"),
    ("Телевизор", "📺", "Развлечения"),
    ("Балкон", "🌿", "Комфорт"),
    ("Лифт", "🛗", "Доступность"),
    ("Бассейн", "🏊", "Отдых"),
    ("Завтрак", "🥐", "Питание"),
    ("Домашние животные", "🐾", "Правила"),
    ("Курение запрещено", "🚭", "Правила"),
    ("Рабочее место", "💻", "Работа"),
    ("Сейф", "🔒", "Безопасность"),
]


class Command(BaseCommand):
    help = "Загружает стандартный набор удобств для объявлений"

    def handle(self, *args, **options):
        created = 0
        for name, icon, category in DEFAULT_AMENITIES:
            _, was_created = Amenity.objects.get_or_create(
                name=name,
                defaults={"icon": icon, "category": category},
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Готово. Создано удобств: {created}"))
