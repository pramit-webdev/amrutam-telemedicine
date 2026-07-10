import os

from slowapi import Limiter
from slowapi.util import get_remote_address

rate_limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    enabled=os.environ.get("ENVIRONMENT") != "testing",
    default_limits=["100/minute"],
)
