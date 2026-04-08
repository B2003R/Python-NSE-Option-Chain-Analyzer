from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class OptionMode(str, Enum):
    """Supported option modes from the legacy application."""

    INDEX = "Index"
    STOCK = "Stock"


@dataclass(frozen=True)
class OptionChainRow:
    """Normalized single strike row used by the analysis engine."""

    strike_price: float
    call_open_interest: int
    call_change_open_interest: int
    put_open_interest: int
    put_change_open_interest: int


@dataclass(frozen=True)
class OptionChainSnapshot:
    """Normalized payload extracted from NSE response."""

    timestamp: str
    underlying_value: float
    rows: List[OptionChainRow]


@dataclass(frozen=True)
class BoundaryStrength:
    """Open-interest boundary value with strike price."""

    strike_price: float
    open_interest: float


@dataclass(frozen=True)
class AnalysisResult:
    """Computed analytics payload for API responses and UI rendering."""

    timestamp: str
    underlying_value: float
    call_sum: float
    put_sum: float
    difference: float
    call_boundary: float
    put_boundary: float
    call_itm_ratio: float
    put_itm_ratio: float
    put_call_ratio: float
    max_call_oi: BoundaryStrength
    max_call_oi_secondary: BoundaryStrength
    max_put_oi: BoundaryStrength
    max_put_oi_secondary: BoundaryStrength
    oi_signal: str
    call_itm_signal: str
    put_itm_signal: str
    call_exits_signal: str
    put_exits_signal: str
