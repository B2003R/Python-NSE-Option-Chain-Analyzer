import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from nse_oca.application import AnalysisInput
from nse_oca.domain.models import AnalysisResult, BoundaryStrength, OptionMode
from nse_oca.persistence.database import Base
from nse_oca.persistence.repository import SnapshotRepository


class SnapshotRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)

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
            analysis = AnalysisResult(
                timestamp="06-Apr-2026 10:00:00",
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


if __name__ == "__main__":
    unittest.main()
