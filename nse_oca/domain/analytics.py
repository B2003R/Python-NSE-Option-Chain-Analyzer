from __future__ import annotations

from typing import List

from .models import AnalysisResult, BoundaryStrength, OptionChainRow, OptionChainSnapshot, OptionMode


class AnalysisError(ValueError):
    """Raised when snapshot data cannot be analyzed reliably."""


def _round_factor(mode: OptionMode) -> int:
    return 1000 if mode == OptionMode.INDEX else 10


def _zero_fix(value: float) -> float:
    return 0.0 if value == -0.0 else value


def _itm_signal(call_change: float, put_change: float) -> str:
    label = "No"
    if put_change > call_change:
        if put_change >= 0:
            if call_change <= 0:
                label = "Yes"
            elif put_change / call_change > 1.5:
                label = "Yes"
        elif call_change != 0 and put_change / call_change < 0.5:
            label = "Yes"
    if call_change <= 0:
        label = "Yes"
    return label


def _find_selected_index(rows: List[OptionChainRow], strike_price: int) -> int:
    for idx, row in enumerate(rows):
        if int(row.strike_price) == int(strike_price):
            return idx
    raise AnalysisError(f"Strike price {strike_price} is not available in the current snapshot")


def _call_change(rows: List[OptionChainRow], index: int) -> int:
    if index < 0 or index >= len(rows):
        return 0
    return rows[index].call_change_open_interest


def _put_change(rows: List[OptionChainRow], index: int) -> int:
    if index < 0 or index >= len(rows):
        return 0
    return rows[index].put_change_open_interest


def _secondary_boundaries(
    rows: List[OptionChainRow],
    call_oi_list: List[int],
    put_oi_list: List[int],
    call_oi_index: int,
    put_oi_index: int,
    round_factor: int,
    max_call_oi: BoundaryStrength,
    max_put_oi: BoundaryStrength,
) -> tuple[BoundaryStrength, BoundaryStrength]:
    if max_call_oi.strike_price == max_put_oi.strike_price:
        return max_call_oi, max_put_oi

    lower = min(put_oi_index, call_oi_index)
    upper = max(put_oi_index, call_oi_index)

    if upper - lower == 1:
        call_secondary = BoundaryStrength(
            strike_price=rows[put_oi_index].strike_price,
            open_interest=round(call_oi_list[put_oi_index] / round_factor, 1),
        )
        put_secondary = BoundaryStrength(
            strike_price=rows[call_oi_index].strike_price,
            open_interest=round(put_oi_list[call_oi_index] / round_factor, 1),
        )
        return call_secondary, put_secondary

    call_candidates = list(range(lower, upper))
    put_candidates = list(range(lower + 1, upper + 1))

    if not call_candidates:
        call_secondary = max_call_oi
    else:
        call_index_secondary = max(call_candidates, key=lambda idx: call_oi_list[idx])
        call_secondary = BoundaryStrength(
            strike_price=rows[call_index_secondary].strike_price,
            open_interest=round(call_oi_list[call_index_secondary] / round_factor, 1),
        )

    if not put_candidates:
        put_secondary = max_put_oi
    else:
        put_index_secondary = max(put_candidates, key=lambda idx: put_oi_list[idx])
        put_secondary = BoundaryStrength(
            strike_price=rows[put_index_secondary].strike_price,
            open_interest=round(put_oi_list[put_index_secondary] / round_factor, 1),
        )

    return call_secondary, put_secondary


def analyze_snapshot(snapshot: OptionChainSnapshot, strike_price: int, mode: OptionMode) -> AnalysisResult:
    """Replicates core indicator calculations from the legacy desktop runtime."""

    if not snapshot.rows:
        raise AnalysisError("Snapshot does not contain any rows")

    rows = sorted(snapshot.rows, key=lambda item: item.strike_price)
    round_factor = _round_factor(mode)

    call_oi_list = [row.call_open_interest for row in rows]
    put_oi_list = [row.put_open_interest for row in rows]

    call_oi_index = call_oi_list.index(max(call_oi_list))
    put_oi_index = put_oi_list.index(max(put_oi_list))

    max_call_oi = BoundaryStrength(
        strike_price=rows[call_oi_index].strike_price,
        open_interest=round(max(call_oi_list) / round_factor, 1),
    )
    max_put_oi = BoundaryStrength(
        strike_price=rows[put_oi_index].strike_price,
        open_interest=round(max(put_oi_list) / round_factor, 1),
    )

    max_call_oi_secondary, max_put_oi_secondary = _secondary_boundaries(
        rows=rows,
        call_oi_list=call_oi_list,
        put_oi_list=put_oi_list,
        call_oi_index=call_oi_index,
        put_oi_index=put_oi_index,
        round_factor=round_factor,
        max_call_oi=max_call_oi,
        max_put_oi=max_put_oi,
    )

    total_call_oi = sum(call_oi_list)
    total_put_oi = sum(put_oi_list)
    put_call_ratio = round(total_put_oi / total_call_oi, 2) if total_call_oi else 0.0

    selected_index = _find_selected_index(rows, strike_price)

    c1 = _call_change(rows, selected_index)
    c2 = _call_change(rows, selected_index + 1)
    c3 = _call_change(rows, selected_index + 2)
    call_sum = _zero_fix(round((c1 + c2 + c3) / round_factor, 1))
    call_boundary = _zero_fix(round(c3 / round_factor, 1))

    p1 = _put_change(rows, selected_index)
    p2 = _put_change(rows, selected_index + 1)
    p3 = _put_change(rows, selected_index + 2)
    p4 = _put_change(rows, selected_index + 4)
    p5 = _call_change(rows, selected_index + 4)
    p6 = _call_change(rows, selected_index - 2)
    p7 = _put_change(rows, selected_index - 2)

    put_sum = _zero_fix(round((p1 + p2 + p3) / round_factor, 1))
    put_boundary = _zero_fix(round(p1 / round_factor, 1))
    difference = _zero_fix(round(call_sum - put_sum, 1))

    call_itm_ratio = _zero_fix(round(p4 / p5, 1)) if p5 else 0.0
    put_itm_ratio = _zero_fix(round(p6 / p7, 1)) if p7 else 0.0

    oi_signal = "Bearish" if call_sum >= put_sum else "Bullish"
    call_itm_signal = _itm_signal(call_change=p5, put_change=p4)
    put_itm_signal = _itm_signal(call_change=p7, put_change=p6)
    call_exits_signal = "Yes" if call_boundary <= 0 or call_sum <= 0 else "No"
    put_exits_signal = "Yes" if put_boundary <= 0 or put_sum <= 0 else "No"

    return AnalysisResult(
        timestamp=snapshot.timestamp,
        underlying_value=snapshot.underlying_value,
        call_sum=call_sum,
        put_sum=put_sum,
        difference=difference,
        call_boundary=call_boundary,
        put_boundary=put_boundary,
        call_itm_ratio=call_itm_ratio,
        put_itm_ratio=put_itm_ratio,
        put_call_ratio=put_call_ratio,
        max_call_oi=max_call_oi,
        max_call_oi_secondary=max_call_oi_secondary,
        max_put_oi=max_put_oi,
        max_put_oi_secondary=max_put_oi_secondary,
        oi_signal=oi_signal,
        call_itm_signal=call_itm_signal,
        put_itm_signal=put_itm_signal,
        call_exits_signal=call_exits_signal,
        put_exits_signal=put_exits_signal,
    )
