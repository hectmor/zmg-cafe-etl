"""Heuristic, non-official classification of SCIAN 722515 establishments.

SCIAN 722515 groups cafeterías, neverías, refresquerías and similares into a
single class; INEGI DENUE never tells them apart. This keyword heuristic over
the commercial name/razon social recovers a likely subtype so the product can
show it, but it is a derived guess, not INEGI data, and must never be
presented as an official attribute.
"""

from __future__ import annotations

import unicodedata

# Checked in this order: a name can mix categories (e.g. "Nevería y Café"),
# and ice cream/soda keywords win over "cafe" because those are exactly the
# subtypes SCIAN 722515 hides and this heuristic exists to surface.
_NEVERIA_KEYWORDS = ("nieve", "neveria", "paleta", "helado")
_REFRESQUERIA_KEYWORDS = ("refresco", "refresqueria", "soda")
_CAFE_KEYWORDS = ("cafe", "coffee", "espresso")


def classify_establishment_kind(name: str | None, razon_social: str | None) -> str:
    """Guess "cafe"/"neveria"/"refresqueria"/"otro" from name keywords.

    Returns "otro" when neither input matches a keyword, including when both
    are None/blank -- never defaults to "cafe" for an ambiguous name.
    """

    haystack = " ".join(part for part in (_normalize(name), _normalize(razon_social)) if part)
    if any(keyword in haystack for keyword in _NEVERIA_KEYWORDS):
        return "neveria"
    if any(keyword in haystack for keyword in _REFRESQUERIA_KEYWORDS):
        return "refresqueria"
    if any(keyword in haystack for keyword in _CAFE_KEYWORDS):
        return "cafe"
    return "otro"


def _normalize(value: str | None) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(character for character in decomposed if not unicodedata.combining(character))
