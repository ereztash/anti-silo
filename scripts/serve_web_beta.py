from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.scan import MAX_BODY_BYTES, ScanRequestError, build_web_report  # noqa: E402


PUBLIC_ROOT = ROOT / "public"


class WebBetaPreviewHandler(SimpleHTTPRequestHandler):
    server_version = "AntiSiloWebPreview/0.1"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(PUBLIC_ROOT), **kwargs)

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/api/scan":
            self._send_json(HTTPStatus.OK, {"status": "ready", "mode": "local-preview"})
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/scan":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ScanRequestError("The request body is empty.")
            if content_length > MAX_BODY_BYTES:
                raise ScanRequestError("The upload exceeds the Web Beta request limit.", 413)
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            self._send_json(HTTPStatus.OK, build_web_report(payload))
        except ScanRequestError as exc:
            self._send_json(exc.status, {"error": str(exc)})
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "The request body must be valid JSON."})
        except Exception:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "The preview scan failed."})


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Serve the Anti-Silo Web Beta locally for development and QA.")
    result.add_argument("--port", type=int, default=8766)
    result.add_argument("--no-browser", action="store_true")
    return result


def main() -> None:
    args = parser().parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), WebBetaPreviewHandler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    if not args.no_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    print(f"Anti-Silo Web Beta preview running at {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
