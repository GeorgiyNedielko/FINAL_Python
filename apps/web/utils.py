from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def validate_uploaded_images(files):
    max_size = settings.LISTING_IMAGE_MAX_SIZE_MB * 1024 * 1024
    max_count = settings.LISTING_IMAGE_MAX_COUNT
    if len(files) > max_count:
        raise ValidationError(f"Максимум {max_count} фотографий за раз.")
    for f in files:
        if f.content_type not in ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"Недопустимый формат: {f.name}. Используйте JPEG, PNG или WebP.")
        if f.size > max_size:
            raise ValidationError(f"Файл {f.name} слишком большой (макс. {settings.LISTING_IMAGE_MAX_SIZE_MB} МБ).")


def check_login_rate_limit(request, identifier: str) -> bool:
    """Returns True if login is allowed."""
    ip = request.META.get("REMOTE_ADDR", "unknown")
    key = f"login_rl:{ip}:{identifier}"
    attempts = cache.get(key, 0)
    return attempts < 10


def record_login_failure(request, identifier: str):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    key = f"login_rl:{ip}:{identifier}"
    cache.set(key, cache.get(key, 0) + 1, timeout=900)


def clear_login_failures(request, identifier: str):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    cache.delete(f"login_rl:{ip}:{identifier}")
