import asyncio
import json
import pytest
from typing import Any, Dict, Optional
from backend.app.main import app


class ASGIResponse:
    def __init__(self, status_code: int, headers: Dict[str, str], body: bytes):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.text = body.decode("utf-8")

    def json(self) -> Any:
        return json.loads(self.text)


class ASGIClient:
    def __init__(self, asgi_app):
        self.app = asgi_app

    def request(
        self,
        method: str,
        path: str,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ASGIResponse:
        return asyncio.run(self._async_request(method, path, json_data, headers))

    async def _async_request(
        self,
        method: str,
        path: str,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ASGIResponse:
        req_headers = []
        body_bytes = b""
        if json_data is not None:
            body_bytes = json.dumps(json_data).encode("utf-8")
            req_headers.append((b"content-type", b"application/json"))
        req_headers.append((b"accept", b"application/json"))

        if headers:
            for k, v in headers.items():
                req_headers.append((k.lower().encode("utf-8"), v.encode("utf-8")))

        query_string = b""
        if "?" in path:
            path, qs = path.split("?", 1)
            query_string = qs.encode("utf-8")

        response_status = 500
        response_headers: Dict[str, str] = {}
        response_body = []

        async def receive():
            return {
                "type": "http.request",
                "body": body_bytes,
                "more_body": False,
            }

        async def send(message):
            nonlocal response_status, response_headers
            if message["type"] == "http.response.start":
                response_status = message["status"]
                for hk, hv in message.get("headers", []):
                    response_headers[hk.decode("utf-8").lower()] = hv.decode("utf-8")
            elif message["type"] == "http.response.body":
                response_body.append(message.get("body", b""))

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method.upper(),
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": query_string,
            "headers": req_headers,
            "app": self.app,
        }

        await self.app(scope, receive, send)
        return ASGIResponse(response_status, response_headers, b"".join(response_body))

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> ASGIResponse:
        return self.request("GET", path, headers=headers)

    def post(self, path: str, json: Optional[Any] = None, headers: Optional[Dict[str, str]] = None) -> ASGIResponse:
        return self.request("POST", path, json_data=json, headers=headers)


@pytest.fixture
def client():
    return ASGIClient(app)
