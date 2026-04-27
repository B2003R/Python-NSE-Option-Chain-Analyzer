import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from nse_oca.application import AnalysisInput
from nse_oca.domain.models import AnalysisResult, BoundaryStrength, OptionMode
from nse_oca.persistence.database import Base
from nse_oca.persistence.models import AnalysisSnapshotORM
from nse_oca.persistence.repository import SnapshotRepository


class SnapshotRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)

    @staticmethod
    def _build_analysis(timestamp: str) -> AnalysisResult:
        return AnalysisResult(
            timestamp=timestamp,
            underlying_value=24200.5,
            call_sum=0.0,
            put_sum=0.1,
            difference=-0.1,
            call_boundary=-0.0,
            put_boundary=0.0,
            call_itm_ratio=-0.5,
            put_itm_ratio=1.5,
            put_call_ratio=1.08,
            max_call_oi=BoundaryStrength(strike_price=120.0, open_interest=1.5),
            max_call_oi_secondary=BoundaryStrength(strike_price=130.0, open_interest=1.4),
            max_put_oi=BoundaryStrength(strike_price=160.0, open_interest=1.8),
            max_put_oi_secondary=BoundaryStrength(strike_price=150.0, open_interest=1.7),
            oi_signal="Bullish",
            call_itm_signal="Yes",
            put_itm_signal="Yes",
            call_exits_signal="Yes",
            put_exits_signal="Yes",
        )

    def test_save_and_read_snapshot(self) -> None:
        session = self.Session()
        try:
            repository = SnapshotRepository(session)
            request = AnalysisInput(
                mode=OptionMode.INDEX,
                symbol="NIFTY",
                expiry_date="10-Apr-2026",
                strike_price=120,
            )
            analysis = self._build_analysis("06-Apr-2026 10:00:00")

            created = repository.save_analysis(request=request, analysis=analysis)
            self.assertIsNotNone(created["id"])

            latest = repository.get_latest(
                mode="Index",
                symbol="NIFTY",
                expiry_date="10-Apr-2026",
                strike_price=120,
            )
            self.assertIsNotNone(latest)
            self.assertEqual(latest["oi_signal"], "Bullish")

            history = repository.get_history(
                mode="Index",
                symbol="NIFTY",
                expiry_date="10-Apr-2026",
                strike_price=120,
                limit=20,
            )
            self.assertEqual(len(history), 1)
        finally:
            session.close()

    def test_history_can_be_filtered_by_created_at(self) -> None:
        session = self.Session()
        try:
            repository = SnapshotRepository(session)
            request = AnalysisInput(
                mode=OptionMode.INDEX,
                symbol="NIFTY",
                expiry_date="10-Apr-2026",
                strike_price=120,
            )

            first = repository.save_analysis(request=request, analysis=self._build_analysis("06-Apr-2026 10:00:00"))
            second = repository.save_analysis(request=request, analysis=self._build_analysis("06-Apr-2026 10:01:00"))

            first_row = session.get(AnalysisSnapshotORM, first["id"])
            second_row = session.get(AnalysisSnapshotORM, second["id"])
            self.assertIsNotNone(first_row)
            self.assertIsNotNone(second_row)

            first_row.created_at = datetime(2026, 4, 6, 10, 0, 0)
            second_row.created_at = datetime(2026, 4, 6, 10, 5, 0)
            session.commit()

            history = repository.get_history(
                mode="Index",
                symbol="NIFTY",
                expiry_date="10-Apr-2026",
                strike_price=120,
                since_created_at=datetime(2026, 4, 6, 10, 4, 0),
                limit=20,
            )

            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["id"], second["id"])
        finally:
            session.close()

    def test_history_filter_accepts_timezone_aware_datetime(self) -> None:
        session = self.Session()
        try:
            repository = SnapshotRepository(session)
            request = AnalysisInput(
                mode=OptionMode.INDEX,
                symbol="NIFTY",
                expiry_date="10-Apr-2026",
                strike_price=120,
            )

            first = repository.save_analysis(request=request, analysis=self._build_analysis("06-Apr-2026 10:00:00"))
            second = repository.save_analysis(request=request, analysis=self._build_analysis("06-Apr-2026 10:01:00"))

            first_row = session.get(AnalysisSnapshotORM, first["id"])
            second_row = session.get(AnalysisSnapshotORM, second["id"])
            self.assertIsNotNone(first_row)
            self.assertIsNotNone(second_row)

            first_row.created_at = datetime(2026, 4, 6, 10, 0, 0)
            second_row.created_at = datetime(2026, 4, 6, 10, 5, 0)
            session.commit()

            history = repository.get_history(
                mode="Index",
                symbol="NIFTY",
                expiry_date="10-Apr-2026",
                strike_price=120,
                since_created_at=datetime(2026, 4, 6, 10, 4, 0, tzinfo=timezone.utc),
                limit=20,
            )

            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["id"], second["id"])
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
