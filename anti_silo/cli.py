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
from .index import write_index
from .ingest import write_ingest
from .pulse import write_pulse
from .promotion import write_enforcement
from .snapshot import run_git_snapshot
from .spine import write_source_spine_todos
from .triangulation import write_triangulation


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="anti-silo", description="Portable trust-surface and triangulation engine.")
    p.add_argument("command", choices=["ingest", "index", "triangulate", "contradiction", "queue", "enforce", "pulse", "eligible", "spine", "snapshot"])
    p.add_argument("--vault", default=".", help="Folder to scan.")
    p.add_argument("--output-vault", default=None, help="Output folder for `ingest` staging.")
    p.add_argument("--config", default=None, help="JSON config path.")
    p.add_argument("--profile", default="default", help="Scan profile: default, research, rag, repo, prompts, cor-sys.")
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
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.command == "enforce" and payload.get("blocked", 0):
        return 2
    if args.command == "snapshot" and payload.get("decision") == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
