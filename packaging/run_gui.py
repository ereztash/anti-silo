from __future__ import annotations

import sys

from anti_silo.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["gui", *sys.argv[1:]]))
