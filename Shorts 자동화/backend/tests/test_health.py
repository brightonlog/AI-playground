from app.api import health as health_api


def test_health_ok(monkeypatch, client):
    monkeypatch.setattr(health_api, "redis_ok", lambda: True)
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": True, "redis": True}


def test_health_degraded_without_redis(monkeypatch, client):
    monkeypatch.setattr(health_api, "redis_ok", lambda: False)
    assert client.get("/api/v1/health").json()["status"] == "degraded"


def test_templates(client):
    templates = client.get("/api/v1/templates").json()
    assert [(t["id"], t["available"]) for t in templates] == [
        ("celeb_item", True),
        ("top3", False),
        ("story", False),
    ]
