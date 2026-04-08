from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from nse_oca.application import AnalysisInput
from nse_oca.domain import AnalysisResult
from nse_oca.persistence.models import AnalysisSnapshotORM, AppSettingORM


def _snapshot_to_dict(snapshot: AnalysisSnapshotORM) -> Dict[str, Any]:
    return {
        "id": snapshot.id,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        "mode": snapshot.mode,
        "symbol": snapshot.symbol,
        "expiry_date": snapshot.expiry_date,
        "strike_price": snapshot.strike_price,
        "server_timestamp": snapshot.server_timestamp,
        "underlying_value": snapshot.underlying_value,
        "call_sum": snapshot.call_sum,
        "put_sum": snapshot.put_sum,
        "difference": snapshot.difference,
        "call_boundary": snapshot.call_boundary,
        "put_boundary": snapshot.put_boundary,
        "call_itm_ratio": snapshot.call_itm_ratio,
        "put_itm_ratio": snapshot.put_itm_ratio,
        "put_call_ratio": snapshot.put_call_ratio,
        "max_call_oi_strike": snapshot.max_call_oi_strike,
        "max_call_oi_value": snapshot.max_call_oi_value,
        "max_call_oi_secondary_strike": snapshot.max_call_oi_secondary_strike,
        "max_call_oi_secondary_value": snapshot.max_call_oi_secondary_value,
        "max_put_oi_strike": snapshot.max_put_oi_strike,
        "max_put_oi_value": snapshot.max_put_oi_value,
        "max_put_oi_secondary_strike": snapshot.max_put_oi_secondary_strike,
        "max_put_oi_secondary_value": snapshot.max_put_oi_secondary_value,
        "oi_signal": snapshot.oi_signal,
        "call_itm_signal": snapshot.call_itm_signal,
        "put_itm_signal": snapshot.put_itm_signal,
        "call_exits_signal": snapshot.call_exits_signal,
        "put_exits_signal": snapshot.put_exits_signal,
    }


class SnapshotRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _apply_result(self, row: AnalysisSnapshotORM, analysis: AnalysisResult) -> None:
        row.server_timestamp = analysis.timestamp
        row.underlying_value = analysis.underlying_value
        row.call_sum = analysis.call_sum
        row.put_sum = analysis.put_sum
        row.difference = analysis.difference
        row.call_boundary = analysis.call_boundary
        row.put_boundary = analysis.put_boundary
        row.call_itm_ratio = analysis.call_itm_ratio
        row.put_itm_ratio = analysis.put_itm_ratio
        row.put_call_ratio = analysis.put_call_ratio
        row.max_call_oi_strike = analysis.max_call_oi.strike_price
        row.max_call_oi_value = analysis.max_call_oi.open_interest
        row.max_call_oi_secondary_strike = analysis.max_call_oi_secondary.strike_price
        row.max_call_oi_secondary_value = analysis.max_call_oi_secondary.open_interest
        row.max_put_oi_strike = analysis.max_put_oi.strike_price
        row.max_put_oi_value = analysis.max_put_oi.open_interest
        row.max_put_oi_secondary_strike = analysis.max_put_oi_secondary.strike_price
        row.max_put_oi_secondary_value = analysis.max_put_oi_secondary.open_interest
        row.oi_signal = analysis.oi_signal
        row.call_itm_signal = analysis.call_itm_signal
        row.put_itm_signal = analysis.put_itm_signal
        row.call_exits_signal = analysis.call_exits_signal
        row.put_exits_signal = analysis.put_exits_signal

    def save_analysis(self, request: AnalysisInput, analysis: AnalysisResult) -> Dict[str, Any]:
        statement = select(AnalysisSnapshotORM).where(
            AnalysisSnapshotORM.mode == request.mode.value,
            AnalysisSnapshotORM.symbol == request.symbol,
            AnalysisSnapshotORM.expiry_date == request.expiry_date,
            AnalysisSnapshotORM.strike_price == request.strike_price,
            AnalysisSnapshotORM.server_timestamp == analysis.timestamp,
        )
        existing = self.session.execute(statement).scalar_one_or_none()

        if existing is None:
            existing = AnalysisSnapshotORM(
                mode=request.mode.value,
                symbol=request.symbol,
                expiry_date=request.expiry_date,
                strike_price=request.strike_price,
                server_timestamp=analysis.timestamp,
                underlying_value=analysis.underlying_value,
                call_sum=0.0,
                put_sum=0.0,
                difference=0.0,
                call_boundary=0.0,
                put_boundary=0.0,
                call_itm_ratio=0.0,
                put_itm_ratio=0.0,
                put_call_ratio=0.0,
                max_call_oi_strike=0.0,
                max_call_oi_value=0.0,
                max_call_oi_secondary_strike=0.0,
                max_call_oi_secondary_value=0.0,
                max_put_oi_strike=0.0,
                max_put_oi_value=0.0,
                max_put_oi_secondary_strike=0.0,
                max_put_oi_secondary_value=0.0,
                oi_signal="",
                call_itm_signal="",
                put_itm_signal="",
                call_exits_signal="",
                put_exits_signal="",
            )
            self.session.add(existing)

        self._apply_result(existing, analysis)
        self.session.commit()
        self.session.refresh(existing)
        return _snapshot_to_dict(existing)

    def get_latest(
        self,
        mode: str,
        symbol: str,
        expiry_date: str,
        strike_price: int,
    ) -> Optional[Dict[str, Any]]:
        statement = (
            select(AnalysisSnapshotORM)
            .where(
                AnalysisSnapshotORM.mode == mode,
                AnalysisSnapshotORM.symbol == symbol,
                AnalysisSnapshotORM.expiry_date == expiry_date,
                AnalysisSnapshotORM.strike_price == strike_price,
            )
            .order_by(desc(AnalysisSnapshotORM.created_at))
            .limit(1)
        )
        snapshot = self.session.execute(statement).scalar_one_or_none()
        if snapshot is None:
            return None
        return _snapshot_to_dict(snapshot)

    def get_history(
        self,
        mode: str,
        symbol: str,
        expiry_date: str,
        strike_price: int,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        statement = (
            select(AnalysisSnapshotORM)
            .where(
                AnalysisSnapshotORM.mode == mode,
                AnalysisSnapshotORM.symbol == symbol,
                AnalysisSnapshotORM.expiry_date == expiry_date,
                AnalysisSnapshotORM.strike_price == strike_price,
            )
            .order_by(desc(AnalysisSnapshotORM.created_at))
            .limit(limit)
        )
        snapshots = self.session.execute(statement).scalars().all()
        return [_snapshot_to_dict(item) for item in snapshots]


class SettingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_settings(self) -> Dict[str, str]:
        rows = self.session.execute(select(AppSettingORM)).scalars().all()
        return {row.key: row.value for row in rows}

    def get_setting(self, key: str) -> Optional[str]:
        row = self.session.get(AppSettingORM, key)
        return None if row is None else row.value

    def upsert_setting(self, key: str, value: str) -> Dict[str, str]:
        row = self.session.get(AppSettingORM, key)
        if row is None:
            row = AppSettingORM(key=key, value=value)
            self.session.add(row)
        else:
            row.value = value

        self.session.commit()
        self.session.refresh(row)
        return {"key": row.key, "value": row.value}
