import asyncio

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ValidationError as PydanticValidationError
from starlette.requests import Request

from kashat.api.errors import (
    AppException,
    NotFoundError,
    ValidationError,
    get_request_id,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    register_exception_handlers,
)


def _make_request(state_id=None, header_id=None):
    headers = []
    if header_id:
        headers.append((b"x-request-id", header_id.encode("utf-8")))
    scope = {"type": "http", "method": "GET", "path": "/test", "headers": headers}
    request = Request(scope)
    if state_id is not None:
        request.state.request_id = state_id
    return request


def test_get_request_id_prefers_state():
    req = _make_request(state_id="state-1", header_id="header-1")
    assert get_request_id(req) == "state-1"
    req2 = _make_request(header_id="header-2")
    assert get_request_id(req2) == "header-2"


def test_app_exception_handler_response_shape():
    req = _make_request(state_id="req-1")
    exc = NotFoundError(resource="Thing", resource_id="123")
    resp = asyncio.run(app_exception_handler(req, exc))
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    payload = resp.body.decode("utf-8")
    assert "not_found" in payload
    assert "Thing" in payload


def test_http_exception_handler_mapping():
    req = _make_request(header_id="req-2")
    exc = HTTPException(status_code=404, detail="missing")
    resp = asyncio.run(http_exception_handler(req, exc))
    assert resp.status_code == 404
    assert "NOT_FOUND" in resp.body.decode("utf-8")

    exc2 = HTTPException(status_code=418, detail="teapot")
    resp2 = asyncio.run(http_exception_handler(req, exc2))
    assert resp2.status_code == 418
    assert "HTTP_418" in resp2.body.decode("utf-8")


def test_validation_exception_handler_details():
    class Payload(BaseModel):
        amount: int

    req = _make_request()
    try:
        Payload(amount="bad")
    except PydanticValidationError as exc:
        resp = asyncio.run(validation_exception_handler(req, exc))
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        body = resp.body.decode("utf-8")
        assert "VALIDATION_ERROR" in body
        assert "amount" in body


def test_generic_exception_handler():
    req = _make_request()
    resp = asyncio.run(generic_exception_handler(req, RuntimeError("boom")))
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "internal_error" in resp.body.decode("utf-8")


def test_register_exception_handlers():
    app = FastAPI()
    register_exception_handlers(app)
    keys = set(app.exception_handlers.keys())
    assert AppException in keys
    assert HTTPException in keys
    assert Exception in keys
