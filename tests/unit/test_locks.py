import pytest

from webwatcher.orchestration.locks import DistributedLockError, company_scan_lock


def test_lock_falls_back_locally_when_redis_unavailable(monkeypatch) -> None:
    import webwatcher.orchestration.locks as locks_mod

    def _raise_from_url(*args, **kwargs):
        raise RuntimeError("redis down")

    monkeypatch.setattr(locks_mod.redis, "from_url", _raise_from_url)

    with company_scan_lock(123):
        with pytest.raises(DistributedLockError):
            with company_scan_lock(123):
                pass

