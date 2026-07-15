from __future__ import annotations

from anti_silo.config import load_config


def test_config_loader_accepts_utf8_bom(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text('\ufeff{"output_dir": "out"}', encoding="utf-8")
    assert load_config(path)["output_dir"] == "out"
