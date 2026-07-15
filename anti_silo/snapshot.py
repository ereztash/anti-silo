from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import output_dir


def run_git_snapshot(vault: Path, config: dict[str, Any], message: str | None = None, sign: bool = False) -> dict[str, Any]:
    out = output_dir(vault, config)
    msg = message or f"Trust snapshot {datetime.now(timezone.utc).date().isoformat()}"
    add = subprocess.run(["git", "add", str(out.relative_to(vault))], cwd=vault, capture_output=True, text=True)
    if add.returncode != 0:
        return {"decision": "failed", "step": "git add", "stderr": add.stderr.strip()}
    commit_cmd = ["git", "commit"]
    if sign:
        commit_cmd.append("-S")
    commit_cmd += ["-m", msg]
    commit = subprocess.run(commit_cmd, cwd=vault, capture_output=True, text=True)
    if commit.returncode != 0:
        return {"decision": "failed", "step": "git commit", "stderr": commit.stderr.strip(), "stdout": commit.stdout.strip()}
    payload = {"decision": "committed", "message": msg, "stdout": commit.stdout.strip()}
    (out / "snapshot.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
