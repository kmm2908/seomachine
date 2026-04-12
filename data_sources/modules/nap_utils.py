"""Shared NAP normalisation and comparison utilities."""

from __future__ import annotations
import re
from typing import Literal

NAPMatchStatus = Literal['match', 'mismatch', 'unknown']


def normalise_phone(phone: str) -> str:
    """Strip non-digit characters for comparison."""
    return re.sub(r'\D', '', phone)


def normalise_address(addr: str) -> str:
    """Lowercase + collapse whitespace for loose comparison."""
    return re.sub(r'\s+', ' ', addr.lower().strip())


def compare_phone(a: str, b: str) -> NAPMatchStatus:
    if not a or not b:
        return 'unknown'
    return 'match' if normalise_phone(a) == normalise_phone(b) else 'mismatch'


def compare_address(a: str, b: str) -> NAPMatchStatus:
    if not a or not b:
        return 'unknown'
    na, nb = normalise_address(a), normalise_address(b)
    return 'match' if (na in nb or nb in na or na == nb) else 'mismatch'


def compare_name(a: str, b: str) -> NAPMatchStatus:
    if not a or not b:
        return 'unknown'
    return 'match' if a.lower().strip() == b.lower().strip() else 'mismatch'
