from __future__ import annotations

from typing import Any, Dict, List

from nse_oca.domain.models import OptionChainRow, OptionChainSnapshot


class OptionChainParseError(ValueError):
    """Raised when NSE response payload cannot be normalized."""


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_expiry_dates(payload: Dict[str, Any]) -> List[str]:
    """Parses expiry dates from either response shape used by NSE endpoints."""

    if isinstance(payload.get("expiryDates"), list):
        return [str(item) for item in payload["expiryDates"]]

    records = payload.get("records")
    if isinstance(records, dict) and isinstance(records.get("expiryDates"), list):
        return [str(item) for item in records["expiryDates"]]

    return []


def parse_option_chain_snapshot(payload: Dict[str, Any], expiry_date: str) -> OptionChainSnapshot:
    records = payload.get("records")
    if not isinstance(records, dict):
        raise OptionChainParseError("Missing records object in option chain response")

    data = records.get("data")
    if not isinstance(data, list):
        raise OptionChainParseError("Missing records.data list in option chain response")

    expiry_filter = expiry_date.strip().lower()
    ce_by_strike: Dict[float, Dict[str, int]] = {}
    pe_by_strike: Dict[float, Dict[str, float]] = {}

    for item in data:
        if not isinstance(item, dict):
            continue

        row_expiry = str(item.get("expiryDates", "")).strip().lower()
        if row_expiry != expiry_filter:
            continue

        ce_payload = item.get("CE")
        if isinstance(ce_payload, dict):
            strike = _to_float(ce_payload.get("strikePrice"))
            ce_by_strike[strike] = {
                "open_interest": _to_int(ce_payload.get("openInterest")),
                "change_open_interest": _to_int(ce_payload.get("changeinOpenInterest")),
            }

        pe_payload = item.get("PE")
        if isinstance(pe_payload, dict):
            strike = _to_float(pe_payload.get("strikePrice"))
            pe_by_strike[strike] = {
                "open_interest": _to_int(pe_payload.get("openInterest")),
                "change_open_interest": _to_int(pe_payload.get("changeinOpenInterest")),
                "underlying_value": _to_float(pe_payload.get("underlyingValue")),
            }

    common_strikes = sorted(set(ce_by_strike).intersection(pe_by_strike))
    if not common_strikes:
        raise OptionChainParseError(
            f"No complete CE/PE records found for expiry date {expiry_date}"
        )

    rows: List[OptionChainRow] = []
    underlying_value = 0.0

    for strike in common_strikes:
        ce_record = ce_by_strike[strike]
        pe_record = pe_by_strike[strike]

        if underlying_value == 0.0 and pe_record.get("underlying_value", 0.0) != 0.0:
            underlying_value = float(pe_record["underlying_value"])

        rows.append(
            OptionChainRow(
                strike_price=strike,
                call_open_interest=int(ce_record["open_interest"]),
                call_change_open_interest=int(ce_record["change_open_interest"]),
                put_open_interest=int(pe_record["open_interest"]),
                put_change_open_interest=int(pe_record["change_open_interest"]),
            )
        )

    if underlying_value == 0.0:
        for strike in common_strikes:
            fallback_value = float(pe_by_strike[strike].get("underlying_value", 0.0))
            if fallback_value != 0.0:
                underlying_value = fallback_value
                break

    timestamp = str(records.get("timestamp", ""))
    if not timestamp:
        raise OptionChainParseError("Missing records.timestamp in option chain response")

    return OptionChainSnapshot(timestamp=timestamp, underlying_value=underlying_value, rows=rows)
