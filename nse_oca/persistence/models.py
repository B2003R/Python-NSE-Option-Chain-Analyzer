from __future__ import annotations

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class AnalysisSnapshotORM(Base):
    __tablename__ = "analysis_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "mode",
            "symbol",
            "expiry_date",
            "strike_price",
            "server_timestamp",
            name="uq_analysis_snapshot_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    expiry_date: Mapped[str] = mapped_column(String(64), nullable=False)
    strike_price: Mapped[int] = mapped_column(Integer, nullable=False)

    server_timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    underlying_value: Mapped[float] = mapped_column(Float, nullable=False)

    call_sum: Mapped[float] = mapped_column(Float, nullable=False)
    put_sum: Mapped[float] = mapped_column(Float, nullable=False)
    difference: Mapped[float] = mapped_column(Float, nullable=False)
    call_boundary: Mapped[float] = mapped_column(Float, nullable=False)
    put_boundary: Mapped[float] = mapped_column(Float, nullable=False)
    call_itm_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    put_itm_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    put_call_ratio: Mapped[float] = mapped_column(Float, nullable=False)

    max_call_oi_strike: Mapped[float] = mapped_column(Float, nullable=False)
    max_call_oi_value: Mapped[float] = mapped_column(Float, nullable=False)
    max_call_oi_secondary_strike: Mapped[float] = mapped_column(Float, nullable=False)
    max_call_oi_secondary_value: Mapped[float] = mapped_column(Float, nullable=False)

    max_put_oi_strike: Mapped[float] = mapped_column(Float, nullable=False)
    max_put_oi_value: Mapped[float] = mapped_column(Float, nullable=False)
    max_put_oi_secondary_strike: Mapped[float] = mapped_column(Float, nullable=False)
    max_put_oi_secondary_value: Mapped[float] = mapped_column(Float, nullable=False)

    oi_signal: Mapped[str] = mapped_column(String(16), nullable=False)
    call_itm_signal: Mapped[str] = mapped_column(String(8), nullable=False)
    put_itm_signal: Mapped[str] = mapped_column(String(8), nullable=False)
    call_exits_signal: Mapped[str] = mapped_column(String(8), nullable=False)
    put_exits_signal: Mapped[str] = mapped_column(String(8), nullable=False)


class AppSettingORM(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
