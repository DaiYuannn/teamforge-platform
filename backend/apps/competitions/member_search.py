"""Search helpers for the organization-wide competition member picker."""

from itertools import islice, product
import re
import unicodedata

from pypinyin import Style, pinyin


_COMPACT_PATTERN = re.compile(r"[\s\-_'\u2019]+")


def normalize_search_text(value) -> str:
    """Normalize user input while preserving Chinese characters."""
    return unicodedata.normalize('NFKC', str(value or '')).strip().casefold()


def compact_search_text(value) -> str:
    """Normalize pinyin-like input and remove common separators."""
    return _COMPACT_PATTERN.sub('', normalize_search_text(value))


def name_pinyin_forms(name: str) -> set[str]:
    """Return full-pinyin and initial forms, including common polyphonic paths."""
    normalized_name = normalize_search_text(name)
    if not normalized_name:
        return set()

    pronunciation_options = pinyin(
        normalized_name,
        style=Style.NORMAL,
        heteronym=True,
        errors=lambda chars: list(chars),
    )
    if not pronunciation_options:
        return set()

    bounded_options = [tuple(dict.fromkeys(options))[:4] for options in pronunciation_options]
    forms: set[str] = set()
    for syllables in islice(product(*bounded_options), 64):
        compact_syllables = [compact_search_text(item) for item in syllables]
        full = ''.join(compact_syllables)
        initials = ''.join(item[:1] for item in compact_syllables if item)
        if full:
            forms.add(full)
        if initials:
            forms.add(initials)
    return forms


def member_matches_search(*, query: str, values: list[str], name: str) -> bool:
    """Apply AND semantics across terms and OR semantics across member fields."""
    normalized_query = normalize_search_text(query)
    if not normalized_query:
        return True

    normalized_values = [normalize_search_text(value) for value in values if value]
    compact_values = [compact_search_text(value) for value in normalized_values]
    pinyin_forms = name_pinyin_forms(name)
    terms = normalized_query.split()

    for term in terms:
        compact_term = compact_search_text(term)
        if not compact_term:
            continue
        if any(term in value for value in normalized_values):
            continue
        if any(compact_term in value for value in compact_values):
            continue
        if any(compact_term in form for form in pinyin_forms):
            continue
        return False
    return True
