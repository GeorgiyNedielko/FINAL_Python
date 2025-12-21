import os
import redis


def get_redis_client() -> redis.Redis:

    url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    return redis.Redis.from_url(url, decode_responses=True)
