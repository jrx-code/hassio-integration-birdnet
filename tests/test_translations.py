"""Every translations/*.json parses and carries exactly the keys of en.json.

A translation lands here as a pull request from someone who copied a file by
hand, so the two things that actually go wrong are syntax (a missing closing
brace, an object pasted twice) and drift (a key renamed in en.json and left
behind everywhere else). Home Assistant fails the whole integration's
translation load on the first of those, and silently shows the English string
for the second, so neither shows up as a test failure anywhere else.

Runs without Home Assistant installed: it only reads JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

TRANSLATIONS = (
    Path(__file__).parent.parent / "custom_components" / "birdnet_go" / "translations"
)
REFERENCE = "en.json"


def _keys(node, prefix: str = "") -> set[str]:
    found = set()
    for key, value in node.items():
        found.add(prefix + key)
        if isinstance(value, dict):
            found |= _keys(value, prefix + key + ".")
    return found


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        pytest.fail(f"{path.name} is not valid JSON: {err}")


def _files() -> list[Path]:
    return sorted(TRANSLATIONS.glob("*.json"))


def test_reference_exists():
    assert (TRANSLATIONS / REFERENCE).is_file(), (
        f"{REFERENCE} is the key reference and must exist"
    )


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
def test_is_valid_json(path: Path):
    assert isinstance(_load(path), dict)


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
def test_keys_match_english(path: Path):
    english = _keys(_load(TRANSLATIONS / REFERENCE))
    theirs = _keys(_load(path))
    missing = sorted(english - theirs)
    extra = sorted(theirs - english)
    assert not missing, f"{path.name} is missing keys present in {REFERENCE}: {missing}"
    assert not extra, f"{path.name} has keys not in {REFERENCE}: {extra}"


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
def test_no_empty_values(path: Path):
    def leaves(node, prefix=""):
        for key, value in node.items():
            if isinstance(value, dict):
                yield from leaves(value, prefix + key + ".")
            else:
                yield prefix + key, value

    empty = [key for key, value in leaves(_load(path)) if not str(value).strip()]
    assert not empty, f"{path.name} has empty strings: {empty}"
