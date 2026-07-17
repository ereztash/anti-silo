from __future__ import annotations

import base64
import json
import threading
from http.server import HTTPServer
from urllib.request import Request, urlopen

import pytest

from api.scan import (
    ScanRequestError,
    _origin_is_allowed,
    _rate_limited,
    _REQUESTS_BY_CLIENT,
    build_web_report,
    handler,
    _safe_relative_path,
)


def _encoded(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


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
            f"http://127.0.0.1:{server.server_port}/",
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
