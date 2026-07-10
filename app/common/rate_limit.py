from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()

storage_uri = "memory://"
if settings.environment == "production" and settings.redis_url:
    storage_uri = settings.redis_url

rate_limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    enabled=settings.environment != "testing",
    default_limits=["100/minute"],
)
