from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from nse_oca.application import AnalysisInput, AnalysisService
from nse_oca.config.app_config import ALLOWED_REFRESH_SECONDS
from nse_oca.domain import OptionMode
from nse_oca.persistence import SessionLocal, SnapshotRepository


@dataclass(frozen=True)
class ScheduledRunConfig:
    mode: OptionMode
    symbol: str
    expiry_date: str
    strike_price: int
    interval_seconds: int = 60
    persist: bool = True


class AnalysisScheduler:
    """Runs recurring analysis jobs and persists snapshots if configured."""

    JOB_ID = "analysis-loop"

    def __init__(
        self,
        analysis_service: AnalysisService,
        session_factory: Any = SessionLocal,
    ) -> None:
        self.analysis_service = analysis_service
        self.session_factory = session_factory
        self.scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
        self.lock = Lock()
        self.current_config: Optional[ScheduledRunConfig] = None
        self.run_started_at: Optional[datetime] = None
        self.last_run_at: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.total_runs: int = 0

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def start_run(self, config: ScheduledRunConfig) -> Dict[str, Any]:
        if config.interval_seconds not in ALLOWED_REFRESH_SECONDS:
            raise ValueError("interval_seconds is not in allowed refresh set")

        with self.lock:
            self.current_config = config
            # Keep second-level precision so DB timestamps from SQLite compare reliably.
            self.run_started_at = datetime.now(tz=timezone.utc).replace(microsecond=0)
            self.last_error = None

        self.scheduler.add_job(
            self._execute_job,
            trigger=IntervalTrigger(seconds=config.interval_seconds),
            id=self.JOB_ID,
            replace_existing=True,
        )

        # Run one cycle immediately so users see the live session start without waiting a full interval.
        self._execute_job()

        return self.status()

    def stop_run(self) -> Dict[str, Any]:
        with self.lock:
            self.current_config = None
            self.run_started_at = None

        if self.scheduler.get_job(self.JOB_ID):
            self.scheduler.remove_job(self.JOB_ID)

        return self.status()

    def run_once_now(self) -> Dict[str, Any]:
        self._execute_job()
        return self.status()

    def status(self) -> Dict[str, Any]:
        with self.lock:
            config = self.current_config
            run_started_at = self.run_started_at.isoformat() if self.run_started_at else None
            last_run_at = self.last_run_at.isoformat() if self.last_run_at else None
            last_error = self.last_error
            total_runs = self.total_runs

        job = self.scheduler.get_job(self.JOB_ID)
        next_run_at = job.next_run_time.isoformat() if job and job.next_run_time else None

        return {
            "running": job is not None,
            "next_run_at": next_run_at,
            "run_started_at": run_started_at,
            "last_run_at": last_run_at,
            "last_error": last_error,
            "total_runs": total_runs,
            "config": {
                "mode": config.mode.value,
                "symbol": config.symbol,
                "expiry_date": config.expiry_date,
                "strike_price": config.strike_price,
                "interval_seconds": config.interval_seconds,
                "persist": config.persist,
            }
            if config
            else None,
        }

    def _execute_job(self) -> None:
        with self.lock:
            config = self.current_config

        if config is None:
            return

        try:
            result = self.analysis_service.analyze_once(
                AnalysisInput(
                    mode=config.mode,
                    symbol=config.symbol,
                    expiry_date=config.expiry_date,
                    strike_price=config.strike_price,
                )
            )

            if config.persist:
                session: Session = self.session_factory()
                try:
                    repository = SnapshotRepository(session)
                    repository.save_analysis(
                        request=AnalysisInput(
                            mode=config.mode,
                            symbol=config.symbol,
                            expiry_date=config.expiry_date,
                            strike_price=config.strike_price,
                        ),
                        analysis=result,
                    )
                finally:
                    session.close()

            with self.lock:
                self.last_run_at = datetime.now(tz=timezone.utc)
                self.last_error = None
                self.total_runs += 1
        except Exception as err:  # noqa: BLE001
            with self.lock:
                self.last_run_at = datetime.now(tz=timezone.utc)
                self.last_error = str(err)
