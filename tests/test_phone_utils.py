from __future__ import annotations

from lotoia.clients.phone_utils import canonical_brazil_phone, phone_lookup_candidates


def test_phone_lookup_candidates_with_and_without_country_code() -> None:
    assert "5566992358330" in phone_lookup_candidates("66992358330")
    assert "66992358330" in phone_lookup_candidates("5566992358330")


def test_canonical_brazil_phone_adds_country_code() -> None:
    assert canonical_brazil_phone("66996870388") == "5566996870388"
