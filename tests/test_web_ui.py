from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path
from subprocess import PIPE, Popen, TimeoutExpired, run
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def test_hosted_results_expose_auditable_score_and_client_artifact() -> None:
    html = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "public" / "app.js").read_text(encoding="utf-8")

    for element_id in (
        'id="score-meter"',
        'id="score-weighted-base"',
        'id="score-duplicate-penalty"',
        'id="score-stop-findings"',
        'id="score-stop-cap"',
        'id="trust-boundary"',
        'id="download-client-report"',
    ):
        assert element_id in html

    assert "function buildClientReport(report)" in script
    assert 'addEventListener("click", downloadClientReport)' in script
    assert "score.methodology" in script
    assert "report.trust_boundary" in script
    assert 'const autoDemo = new URLSearchParams(window.location.search).get("demo") === "1"' in script
    assert 'behavior: autoDemo ? "auto" : "smooth"' in script


def test_web_preview_script_can_be_invoked_directly() -> None:
    result = run(
        [sys.executable, str(ROOT / "scripts" / "serve_web_beta.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "--no-browser" in result.stdout


def test_web_preview_serves_ui_and_demo_api() -> None:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]

    process = Popen(
        [
            sys.executable,
            str(ROOT / "scripts" / "serve_web_beta.py"),
            "--port",
            str(port),
            "--no-browser",
        ],
        cwd=ROOT,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
    )
    try:
        for _ in range(40):
            try:
                with urlopen(f"http://127.0.0.1:{port}/api/scan", timeout=1) as response:
                    ready = json.loads(response.read().decode("utf-8"))
                break
            except OSError:
                time.sleep(0.05)
        else:
            raise AssertionError("Web Beta preview did not start")

        assert ready == {"status": "ready", "mode": "local-preview"}
        with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
            html = response.read().decode("utf-8")
        assert 'id="run-demo"' in html

        request = Request(
            f"http://127.0.0.1:{port}/api/scan",
            data=json.dumps({"demo": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            report = json.loads(response.read().decode("utf-8"))
        assert report["demo"] is True
        assert report["readiness_score"]["components"]
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
