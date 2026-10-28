from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import AppError, register_error_handlers

app = FastAPI()
register_error_handlers(app)


@app.get("/app-error")
def _app_error():
    raise AppError(409, "invalid_state", "상태가 맞지 않습니다")


@app.get("/boom")
def _boom():
    raise RuntimeError("secret sk-xxx")


@app.get("/typed")
def _typed(n: int):
    return n


client = TestClient(app, raise_server_exceptions=False)


def test_app_error_shape():
    r = client.get("/app-error")
    assert r.status_code == 409
    assert r.json() == {"error": "invalid_state", "detail": "상태가 맞지 않습니다"}


def test_not_found_shape():
    r = client.get("/nope")
    assert r.status_code == 404
    assert r.json()["error"] == "not_found"


def test_validation_shape():
    r = client.get("/typed?n=abc")
    assert r.status_code == 422
    assert r.json()["error"] == "validation_error"


def test_unhandled_hides_message():
    r = client.get("/boom")
    assert r.status_code == 500
    assert r.json() == {"error": "internal_error", "detail": "서버 내부 오류"}
