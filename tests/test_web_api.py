from __future__ import annotations

import base64

import pytest

from api.scan import ScanRequestError, _safe_relative_path, build_web_report


def _encoded(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def test_safe_relative_path_rejects_traversal_and_absolute_paths() -> None:
    for value in ("../secret.md", "/etc/passwd", "C:/secret.md", "folder/../../secret.md"):
        with pytest.raises(ScanRequestError):
            _safe_relative_path(value)


def test_web_report_runs_existing_preflight_without_leaking_temp_paths() -> None:
    report = build_web_report(
        {
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
    assert "source_root" not in report
    assert "staged_vault" not in report
    assert "downloads" not in report


def test_web_report_rejects_missing_files() -> None:
    with pytest.raises(ScanRequestError, match="at least one"):
        build_web_report({"files": []})
