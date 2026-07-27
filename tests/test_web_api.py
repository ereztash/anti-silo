from __future__ import annotations

import base64
from http.client import HTTPConnection
import json
import threading
from http.server import HTTPServer
from urllib.request import Request, urlopen

import pytest

from api.scan import (
    ScanRequestError,
    _client_identity,
    _origin_is_allowed,
    _rate_limited,
    _REQUESTS_BY_CLIENT,
    build_web_report,
    handler,
    _safe_relative_path,
)


class _Headers(dict):
    """Mimics the case-insensitive lookup of http.client message headers."""

    def get(self, key, default=None):  # type: ignore[override]
        return dict.get(self, key.lower(), default)


def _encoded(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def test_spoofed_x_forwarded_for_cannot_change_the_rate_limit_bucket() -> None:
    # Previously the identity was the FIRST X-Forwarded-For entry, which any
    # caller can set - so varying it gave an unlimited supply of fresh buckets.
    identities = {
        _client_identity(_Headers({"x-forwarded-for": f"10.0.0.{octet}"}), "203.0.113.9")
        for octet in range(25)
    }
    assert identities == {"203.0.113.9"}


def test_platform_set_client_header_is_used_and_beats_spoofed_forwarded_for() -> None:
    headers = _Headers({"x-vercel-forwarded-for": "198.51.100.7", "x-forwarded-for": "1.2.3.4"})
    assert _client_identity(headers, "203.0.113.9") == "198.51.100.7"


def test_rate_limit_actually_blocks_a_spoofing_caller() -> None:
    _REQUESTS_BY_CLIENT.clear()
    blocked = 0
    for attempt in range(20):
        client = _client_identity(_Headers({"x-forwarded-for": f"10.0.0.{attempt}"}), "198.51.100.42")
        if _rate_limited(client):
            blocked += 1
    _REQUESTS_BY_CLIENT.clear()
    assert blocked > 0


def test_safe_relative_path_rejects_traversal_and_absolute_paths() -> None:
    for value in ("../secret.md", "/etc/passwd", "C:/secret.md", "folder/../../secret.md"):
        with pytest.raises(ScanRequestError):
            _safe_relative_path(value)


def test_web_report_runs_existing_preflight_without_leaking_temp_paths() -> None:
    report = build_web_report(
        {
            "consent": True,
            "project": {
                "client_name": "Demo Client",
                "project_name": "Support RAG",
                "consultant_name": "Demo Studio",
            },
            "files": [
                {
                    "path": "sources/policy.txt",
                    "content_base64": _encoded(b"client source note"),
                },
                {
                    "path": "slides/deck.pptx",
                    "content_base64": "",
                },
            ],
        }
    )

    assert report["project"]["client_name"] == "Demo Client"
    assert report["files"] == 1
    assert report["diagnostics"]["counts"]["unsupported_files"] == 1
    assert report["privacy"]["stored"] is False
    assert report["input_mode"] == "web_upload"
    assert report["demo"] is False
    assert "source_root" not in report
    assert "staged_vault" not in report
    assert "downloads" not in report


def test_web_report_rejects_missing_files() -> None:
    with pytest.raises(ScanRequestError, match="at least one"):
        build_web_report({"consent": True, "files": []})


def test_web_report_requires_explicit_cloud_processing_consent() -> None:
    with pytest.raises(ScanRequestError, match="consent"):
        build_web_report(
            {
                "files": [
                    {
                        "path": "note.txt",
                        "content_base64": _encoded(b"private client note"),
                    }
                ]
            }
        )


def test_demo_runs_without_user_files_or_consent() -> None:
    report = build_web_report({"demo": True})

    assert report["demo"] is True
    assert report["files"] == 6
    assert report["diagnostics"]["counts"]["unsupported_files"] == 1
    assert report["diagnostics"]["counts"]["duplicate_files"] == 1
    assert report["project"]["client_name"] == "Demo Client"


def test_origin_and_in_memory_rate_limit_guards() -> None:
    assert _origin_is_allowed("https://anti-silo.vercel.app", "anti-silo.vercel.app")
    assert _origin_is_allowed("http://127.0.0.1:3000", "127.0.0.1:3000")
    assert not _origin_is_allowed("https://attacker.example", "anti-silo.vercel.app")

    client = "rate-limit-test"
    _REQUESTS_BY_CLIENT.pop(client, None)
    for index in range(6):
        assert not _rate_limited(client, now=float(index))
    assert _rate_limited(client, now=7.0)
    assert not _rate_limited(client, now=700.0)


def test_vercel_http_handler_serves_demo_report() -> None:
    _REQUESTS_BY_CLIENT.clear()
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = json.dumps({"demo": True}).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/scan",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            report = json.loads(response.read().decode("utf-8"))

        assert response.status == 200
        assert report["demo"] is True
        assert report["readiness_score"]["score"] >= 0
        assert report["risk_register"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_vercel_http_handler_redirects_root_and_rejects_other_routes() -> None:
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request("GET", "/?demo=1")
        response = connection.getresponse()
        assert response.status == 307
        assert response.getheader("Location") == "/index.html?demo=1"
        response.read()

        connection.request("POST", "/", body=b"{}", headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        assert response.status == 404
        response.read()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
