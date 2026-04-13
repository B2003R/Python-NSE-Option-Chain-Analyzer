import unittest
from typing import Any, cast

from nse_oca.domain import BoundaryStrength, OptionMode
from nse_oca.domain.models import AnalysisResult
from nse_oca.worker.scheduler_service import AnalysisScheduler, ScheduledRunConfig


class _FakeAnalysisService:
    def analyze_once(self, _request):
        return AnalysisResult(
            timestamp="10-Apr-2026 13:16:08",
            underlying_value=24000.0,
            call_sum=10.0,
            put_sum=12.0,
            difference=-2.0,
            call_boundary=2.0,
            put_boundary=4.0,
            call_itm_ratio=0.1,
            put_itm_ratio=0.2,
            put_call_ratio=1.2,
            max_call_oi=BoundaryStrength(strike_price=24000.0, open_interest=100.0),
            max_call_oi_secondary=BoundaryStrength(strike_price=24100.0, open_interest=90.0),
            max_put_oi=BoundaryStrength(strike_price=23900.0, open_interest=110.0),
            max_put_oi_secondary=BoundaryStrength(strike_price=23800.0, open_interest=95.0),
            oi_signal="Bullish",
            call_itm_signal="Yes",
            put_itm_signal="No",
            call_exits_signal="No",
            put_exits_signal="No",
        )


class SchedulerServiceTests(unittest.TestCase):
    def test_start_run_executes_immediately(self) -> None:
        scheduler = AnalysisScheduler(cast(Any, _FakeAnalysisService()))
        scheduler.start()
        try:
            status = scheduler.start_run(
                ScheduledRunConfig(
                    mode=OptionMode.INDEX,
                    symbol="NIFTY",
                    expiry_date="13-Apr-2026",
                    strike_price=24000,
                    interval_seconds=60,
                    persist=False,
                )
            )

            self.assertTrue(status["running"])
            self.assertEqual(status["total_runs"], 1)
            self.assertIsNotNone(status["last_run_at"])
        finally:
            scheduler.stop_run()
            scheduler.shutdown()


if __name__ == "__main__":
    unittest.main()
