from __future__ import annotations
import re
from typing import Iterable, Tuple
import difflib

try:
    from rapidfuzz import process, fuzz  # type: ignore
except Exception:  # pragma: no cover
    process = None  # type: ignore
    fuzz = None  # type: ignore


_PACK_PAT = re.compile(r"\b(\d+\s*(g|gm|kg|ml|l|lt))\b", re.I)
_WHITESPACE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    n = name or ""
    n = n.lower()
    n = _PACK_PAT.sub("", n)
    n = re.sub(r"[^a-z0-9\s]+", " ", n)
    n = _WHITESPACE.sub(" ", n).strip()
    return n


def resolve_alias(name: str, existing: Iterable[str], *, threshold: int = 80) -> Tuple[str, bool]:
    """
    Return (canonical_name, changed?). If a close existing match is found, use it.
    Uses RapidFuzz if available, else falls back to normalized exact match.
    """
    if not name:
        return name, False
    base = normalize_name(name)
    if process is None:
        # Use difflib on normalized strings
        norm_map = {normalize_name(ex): ex for ex in existing}
        choices = list(norm_map.keys())
        if not choices:
            return name, False
        # difflib ratio on tokenized strings (close_matches returns list)
        match = difflib.get_close_matches(base, choices, n=1, cutoff=threshold/100.0)
        if match:
            ex = norm_map.get(match[0]) or name
            return ex, ex != name
        # fallback to exact normalized match
        if base in norm_map:
            ex = norm_map[base]
            return ex, ex != name
        return name, False
    choices = list(existing)
    if not choices:
        return name, False
    norm_choices = [normalize_name(c) for c in choices]
    match = process.extractOne(base, norm_choices, scorer=fuzz.token_sort_ratio)
    if match and match[1] >= threshold:
        # Map back by index
        try:
            idx = norm_choices.index(match[0])
            c = choices[idx]
            return c, c != name
        except Exception:
            pass
    return name, False
