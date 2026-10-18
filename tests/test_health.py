"""The health check and the API documentation switch (#185).

/api/health is what the container platform and the uptime monitor call. It
must work without signing in, say only "ok" or "unavailable", and never leak
an error's text. /docs and /openapi.json map every route, so they are off
unless API_DOCS is set.
"""

import pytest


def test_health_answers_without_signing_in(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_503_and_says_nothing_more_when_the_database_is_down(client, monkeypatch):
    import main

    class Broken:
        def __enter__(self):
            raise RuntimeError("could not connect to server at 10.0.0.5:5432, password for dixpertia_app")

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(main, "SessionLocal", Broken)
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}, "no host, role or error text"


def test_health_is_not_rate_limited(client, monkeypatch):
    """A refusing health check would get a healthy container restarted."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "PUBLIC_REQUESTS_PER_MINUTE", 1)
    assert all(client.get("/api/health").status_code == 200 for _ in range(3))


def test_api_documentation_is_off_by_default(client):
    from app.core.config import settings

    if settings.API_DOCS:
        pytest.skip("API_DOCS is set in this environment (a developer's .env)")
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404, path
