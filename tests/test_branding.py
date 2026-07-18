from __future__ import annotations

import pytest

from anti_silo.branding import BrandingStore


def test_branding_defaults_to_empty(tmp_path) -> None:
    store = BrandingStore(tmp_path / "branding.json")
    assert store.get() == {"business_name": "", "logo_data_uri": ""}


def test_branding_persists_across_store_instances(tmp_path) -> None:
    path = tmp_path / "branding.json"
    store = BrandingStore(path)
    store.set("Acme Consulting", "data:image/png;base64,aGVsbG8=")

    reopened = BrandingStore(path)
    assert reopened.get() == {"business_name": "Acme Consulting", "logo_data_uri": "data:image/png;base64,aGVsbG8="}


def test_branding_rejects_disallowed_logo_type(tmp_path) -> None:
    store = BrandingStore(tmp_path / "branding.json")
    with pytest.raises(ValueError):
        store.set("Acme", "data:application/pdf;base64,aGVsbG8=")


def test_branding_rejects_oversized_logo(tmp_path) -> None:
    store = BrandingStore(tmp_path / "branding.json")
    oversized = "data:image/png;base64," + "a" * 400_000
    with pytest.raises(ValueError):
        store.set("Acme", oversized)


def test_branding_business_name_is_cleaned_and_capped(tmp_path) -> None:
    store = BrandingStore(tmp_path / "branding.json")
    result = store.set("  Acme   Consulting  \n\n", "")
    assert result["business_name"] == "Acme Consulting"


def test_branding_empty_logo_is_allowed_to_clear_it(tmp_path) -> None:
    store = BrandingStore(tmp_path / "branding.json")
    store.set("Acme", "data:image/png;base64,aGVsbG8=")
    cleared = store.set("Acme", "")
    assert cleared["logo_data_uri"] == ""
