from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .config import apply_profile, load_config
from .contradiction import write_contradiction_penalties
from .evidence_queue import write_queue
from .eligible import write_eligible_sources
from .gui import serve_gui
from .index import write_index
from .ingest import write_ingest
from .pulse import write_pulse
from .promotion import write_enforcement
from .report_labels import write_localized_outputs
from .snapshot import run_git_snapshot
from .spine import write_source_spine_todos
from .triangulation import write_triangulation


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="anti-silo", description="Portable trust-surface and triangulation engine.")
    p.add_argument("command", choices=["gui", "brain", "ingest", "index", "triangulate", "contradiction", "queue", "enforce", "pulse", "eligible", "spine", "snapshot"])
    p.add_argument("--vault", default=".", help="Folder to scan.")
    p.add_argument("--output-vault", default=None, help="Output folder for `ingest` staging.")
    p.add_argument("--config", default=None, help="JSON config path.")
    p.add_argument("--profile", default="default", help="Scan profile: default, research, rag, repo, prompts, cor-sys.")
    p.add_argument("--lang", default="en", choices=["en", "he"], help="Report language for localized companion outputs.")
    p.add_argument("--host", default="127.0.0.1", help="Host for `gui` or `brain`; defaults to local-only 127.0.0.1.")
    p.add_argument("--port", type=int, default=8765, help="Port for `gui` or `brain`.")
    p.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically for `gui` or `brain`.")
    p.add_argument("--message", default=None, help="Git snapshot commit message.")
    p.add_argument("--sign", action="store_true", help="Sign the Git snapshot commit.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    vault = Path(args.vault).resolve()
    try:
        config = apply_profile(load_config(args.config), args.profile)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.command == "gui":
        serve_gui(config, host=args.host, port=args.port, open_browser=not args.no_browser)
        return 0
    if args.command == "brain":
        serve_gui(config, host=args.host, port=args.port, open_browser=not args.no_browser, initial_view="brain")
        return 0
    if args.command == "ingest":
        payload = write_ingest(vault, config, output_vault=Path(args.output_vault).resolve() if args.output_vault else None)
    elif args.command == "index":
        payload = write_index(vault, config)
    elif args.command == "triangulate":
        payload = write_triangulation(vault, config)
    elif args.command == "queue":
        payload = write_queue(vault, config)
    elif args.command == "contradiction":
        payload = write_contradiction_penalties(vault, config)
    elif args.command == "enforce":
        payload = write_enforcement(vault, config)
    elif args.command == "eligible":
        payload = write_eligible_sources(vault, config)
    elif args.command == "spine":
        payload = write_source_spine_todos(vault, config)
    elif args.command == "snapshot":
        payload = run_git_snapshot(vault, config, message=args.message, sign=args.sign)
    else:
        payload = write_pulse(vault, config)
    if args.lang != "en" and args.command in {"pulse", "triangulate", "enforce", "queue", "eligible", "spine", "contradiction"}:
        localized = write_localized_outputs(vault, payload if args.command == "pulse" else write_pulse(vault, config), lang=args.lang, config=config)
        if localized:
            payload["localized_outputs"] = localized
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.command == "enforce" and payload.get("blocked", 0):
        return 2
    if args.command == "snapshot" and payload.get("decision") == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
