import unittest

from nse_oca.domain.analytics import analyze_snapshot
from nse_oca.domain.models import OptionChainRow, OptionChainSnapshot, OptionMode


class AnalyzeSnapshotTests(unittest.TestCase):
    def test_analyze_snapshot_returns_expected_indicators(self) -> None:
        snapshot = OptionChainSnapshot(
            timestamp="06-Apr-2026 10:00:00",
            underlying_value=24200.5,
            rows=[
                OptionChainRow(100, 1000, 5, 900, -5),
                OptionChainRow(110, 1100, 10, 950, -3),
                OptionChainRow(120, 1500, 20, 1200, 30),
                OptionChainRow(130, 1400, 15, 1300, 25),
                OptionChainRow(140, 1300, -10, 1600, 10),
                OptionChainRow(150, 1250, -20, 1700, 5),
                OptionChainRow(160, 1200, -30, 1800, 40),
            ],
        )

        result = analyze_snapshot(snapshot=snapshot, strike_price=120, mode=OptionMode.INDEX)

        self.assertEqual(result.call_sum, 0.0)
        self.assertEqual(result.put_sum, 0.1)
        self.assertEqual(result.difference, -0.1)
        self.assertEqual(result.put_call_ratio, 1.08)
        self.assertEqual(result.oi_signal, "Bullish")
        self.assertEqual(result.call_itm_signal, "Yes")
        self.assertEqual(result.put_itm_signal, "Yes")
        self.assertEqual(result.call_exits_signal, "Yes")
        self.assertEqual(result.put_exits_signal, "Yes")


if __name__ == "__main__":
    unittest.main()
