from webwatcher.core.config import get_settings


def test_settings_uses_redis_service_url(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://user:pass@localhost:5432/dbname")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.effective_database_url.startswith("postgresql+asyncpg://")
    get_settings.cache_clear()

