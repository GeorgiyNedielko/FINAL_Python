# Mieten — платформа аренды жилья

Полноценный сайт бронирования жилья (аналог Booking/Airbnb): веб-интерфейс, REST API, оплата, чат, отзывы.

## Стек

- **Backend:** Django 5, DRF, SimpleJWT  
- **БД:** MySQL (SQLite для CI/тестов)  
- **Кэш/очередь:** Redis, Celery + Beat  
- **Фронтенд:** Django Templates + CSS  
- **Оплата:** Stripe Checkout (демо-режим без ключей)  
- **Деплой:** Docker, Gunicorn, WhiteNoise, Nginx (prod)

## Возможности

| Модуль | Функции |
|--------|---------|
| **Поиск** | Город, даты, гости, цена, удобства, мгновенное бронирование |
| **Объявления** | Фото, удобства, карта (lat/lng), похожие объявления |
| **Бронирование** | Заявка → подтверждение / instant book → оплата |
| **Отзывы** | Арендатор о жилье, хозяин о госте |
| **Сообщения** | Чат арендатор ↔ арендодатель |
| **API** | `/api/` + Swagger `/api/docs/` |
| **Админка** | Полное управление, блокировка пользователей |

## Быстрый старт (локально)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env          # заполните переменные

docker compose up -d db redis
python manage.py migrate
python manage.py load_amenities
python manage.py runserver
```

Сайт: http://127.0.0.1:8000/

В отдельных терминалах:
```bash
celery -A core worker -l info
celery -A core beat -l info
```

## Docker (полный стек)

```bash
docker compose up -d --build
```

Сайт: http://localhost:8000

**Продакшен с Nginx:**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Переменные окружения (.env)

| Переменная | Описание |
|------------|----------|
| `SECRET_KEY` | Секрет Django |
| `DEBUG` | `0` в продакшене |
| `ALLOWED_HOSTS` | Домены через запятую |
| `USE_TLS` | `1` за HTTPS-прокси |
| `MYSQL_*`, `DB_HOST`, `DB_PORT` | MySQL |
| `REDIS_URL` | Redis |
| `EMAIL_*` | SMTP для писем |
| `STRIPE_*` | Оплата (опционально) |
| `SENTRY_DSN` | Мониторинг ошибок (опционально) |
| `CORS_ALLOWED_ORIGINS` | Для мобильного/SPA API |

## Тесты и CI

```bash
set USE_SQLITE=1
python manage.py migrate
pytest -q
```

GitHub Actions запускает проверки при push в `main`.

## Резервное копирование БД

```bash
mkdir backups
./scripts/backup_db.sh
```

## Роли пользователей

- **tenant** — ищет и бронирует жильё  
- **landlord** — размещает объявления, подтверждает брони  

## API

- Документация: `/api/docs/`  
- JWT: `POST /api/login/`, `POST /api/register/`, `POST /api/refresh/`
