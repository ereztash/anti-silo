from __future__ import annotations

from anti_silo.config import apply_profile, load_config


def test_config_loader_accepts_utf8_bom(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text('\ufeff{"output_dir": "out"}', encoding="utf-8")
    assert load_config(path)["output_dir"] == "out"


def test_profile_merges_excludes_and_sets_active_profile() -> None:
    config = {"exclude_dirs": ["node_modules"], "profiles": {"repo": {"exclude_dirs": [".pytest_cache"]}}}
    profiled = apply_profile(config, "repo")
    assert profiled["active_profile"] == "repo"
    assert set(profiled["exclude_dirs"]) == {"node_modules", ".pytest_cache"}


def test_unknown_profile_is_rejected() -> None:
    config = {"profiles": {"default": {}}}
    try:
        apply_profile(config, "missing")
    except ValueError as exc:
        assert "Unknown profile" in str(exc)
    else:
        raise AssertionError("missing profile should be rejected")


def test_cor_sys_profile_adds_graph_native_corroboration_markers() -> None:
    config = load_config()
    profiled = apply_profile(config, "cor-sys")

    assert "שורת פנקס" not in config["corroboration_markers"]
    assert "שורת פנקס" in profiled["corroboration_markers"]
    assert "corroborated" in profiled["corroboration_markers"]
