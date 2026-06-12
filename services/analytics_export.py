"""Analytics export utilities.

Used by Sprint 7 ING007B.
Exports must reflect the exact applied filters from the analytics dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AnalyticsFilters:
    date_from: Optional[str]  # MM/DD/YYYY
    date_to: Optional[str]    # MM/DD/YYYY
    violation_type: str
    barangay: str


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def render_filters_summary(filters: AnalyticsFilters) -> List[Tuple[str, str]]:
    """Return list of (label, value) for exports."""
    return [
        ("Date From", _safe_str(filters.date_from) or "All"),
        ("Date To", _safe_str(filters.date_to) or "All"),
        ("Violation Type", _safe_str(filters.violation_type) or "All"),
        ("Barangay", _safe_str(filters.barangay) or "All"),
    ]

