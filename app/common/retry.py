from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from sqlalchemy.exc import OperationalError, TimeoutError
from tenacity import retry as tenacity_retry
from tenacity import retry_if_exception_type, stop_after_attempt, wait_exponential

DB_RETRY = tenacity_retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((OperationalError, TimeoutError)),
    reraise=True,
)

CACHE_RETRY = tenacity_retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    retry=retry_if_exception_type((RedisError, RedisConnectionError)),
    reraise=True,
)

PAYMENT_RETRY = tenacity_retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.1, min=0.1, max=0.4),
    retry=retry_if_exception_type((OperationalError, TimeoutError)),
    reraise=True,
)

NOTIFICATION_RETRY = tenacity_retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=16),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
