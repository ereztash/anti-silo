from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .evidence_queue import write_queue
from .index import write_index
from .pulse import write_pulse
from .triangulation import write_triangulation


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="anti-silo", description="Portable trust-surface and triangulation engine.")
    p.add_argument("command", choices=["index", "triangulate", "queue", "pulse"])
    p.add_argument("--vault", default=".", help="Folder to scan.")
    p.add_argument("--config", default=None, help="JSON config path.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    vault = Path(args.vault).resolve()
    config = load_config(args.config)
    if args.command == "index":
        payload = write_index(vault, config)
    elif args.command == "triangulate":
        payload = write_triangulation(vault, config)
    elif args.command == "queue":
        payload = write_queue(vault, config)
    else:
        payload = write_pulse(vault, config)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
