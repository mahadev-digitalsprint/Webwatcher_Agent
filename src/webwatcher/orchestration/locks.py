import uuid
from contextlib import contextmanager

import redis

from webwatcher.core.config import get_settings


class DistributedLockError(RuntimeError):
    pass


@contextmanager
def company_scan_lock(company_id: int, ttl_seconds: int = 900):
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    key = f"lock:company:{company_id}:scan"
    token = str(uuid.uuid4())
    acquired = client.set(key, token, nx=True, ex=ttl_seconds)
    if not acquired:
        raise DistributedLockError(f"Company {company_id} already has an active lock.")
    try:
        yield
    finally:
        current = client.get(key)
        if current == token:
            client.delete(key)

