import uuid
from contextlib import contextmanager
from threading import Lock

import redis

from webwatcher.core.config import get_settings


class DistributedLockError(RuntimeError):
    pass


_local_guard = Lock()
_local_active_company_ids: set[int] = set()


@contextmanager
def company_scan_lock(company_id: int, ttl_seconds: int = 900):
    settings = get_settings()
    key = f"lock:company:{company_id}:scan"
    token = str(uuid.uuid4())

    try:
        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        acquired = client.set(key, token, nx=True, ex=ttl_seconds)
        if not acquired:
            raise DistributedLockError(f"Company {company_id} already has an active lock.")
        try:
            yield
        finally:
            try:
                current = client.get(key)
                if current == token:
                    client.delete(key)
            except Exception:
                pass
        return
    except DistributedLockError:
        raise
    except Exception:
        # Local fallback when Redis is unavailable.
        with _local_guard:
            if company_id in _local_active_company_ids:
                raise DistributedLockError(
                    f"Company {company_id} already has an active local lock."
                ) from None
            _local_active_company_ids.add(company_id)
        try:
            yield
        finally:
            with _local_guard:
                _local_active_company_ids.discard(company_id)
