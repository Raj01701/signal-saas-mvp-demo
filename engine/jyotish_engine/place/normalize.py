"""Text keys for place search."""

from __future__ import annotations

import unicodedata


def normalize(text: str) -> str:
    """Case- and accent-insensitive key: 'Bengaluru', 'bengaluru' and 'Bengalūru' match."""
    decomposed = unicodedata.normalize("NFKD", text.casefold().strip())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
