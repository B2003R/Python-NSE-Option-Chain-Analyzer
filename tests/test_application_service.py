import unittest

from nse_oca.application import AnalysisInput, AnalysisService
from nse_oca.domain import OptionMode


class FakeNseClient:
    def fetch_symbols(self):
        return {"indices": ["NIFTY"], "stocks": ["RELIANCE"]}

    def fetch_expiry_dates(self, symbol: str):
        return ["10-Apr-2026"]

    def fetch_option_chain(self, symbol: str, expiry: str, mode: OptionMode):
        del symbol, mode
        return {
            "records": {
                "timestamp": "06-Apr-2026 10:00:00",
                "data": [
                    {
                        "expiryDates": expiry,
                        "CE": {"strikePrice": 100, "openInterest": 1000, "changeinOpenInterest": 5},
                        "PE": {
                            "strikePrice": 100,
                            "openInterest": 900,
                            "changeinOpenInterest": -5,
                            "underlyingValue": 24200.5,
                        },
                    },
                    {
                        "expiryDates": expiry,
                        "CE": {"strikePrice": 110, "openInterest": 1100, "changeinOpenInterest": 10},
                        "PE": {
                            "strikePrice": 110,
                            "openInterest": 950,
                            "changeinOpenInterest": -3,
                            "underlyingValue": 24200.5,
                        },
                    },
                    {
                        "expiryDates": expiry,
                        "CE": {"strikePrice": 120, "openInterest": 1500, "changeinOpenInterest": 20},
                        "PE": {
                            "strikePrice": 120,
                            "openInterest": 1200,
                            "changeinOpenInterest": 30,
                            "underlyingValue": 24200.5,
                        },
                    },
                    {
                        "expiryDates": expiry,
                        "CE": {"strikePrice": 130, "openInterest": 1400, "changeinOpenInterest": 15},
                        "PE": {
                            "strikePrice": 130,
                            "openInterest": 1300,
                            "changeinOpenInterest": 25,
                            "underlyingValue": 24200.5,
                        },
                    },
                    {
                        "expiryDates": expiry,
                        "CE": {"strikePrice": 140, "openInterest": 1300, "changeinOpenInterest": -10},
                        "PE": {
                            "strikePrice": 140,
                            "openInterest": 1600,
                            "changeinOpenInterest": 10,
                            "underlyingValue": 24200.5,
                        },
                    },
                    {
                        "expiryDates": expiry,
                        "CE": {"strikePrice": 150, "openInterest": 1250, "changeinOpenInterest": -20},
                        "PE": {
                            "strikePrice": 150,
                            "openInterest": 1700,
                            "changeinOpenInterest": 5,
                            "underlyingValue": 24200.5,
                        },
                    },
                    {
                        "expiryDates": expiry,
                        "CE": {"strikePrice": 160, "openInterest": 1200, "changeinOpenInterest": -30},
                        "PE": {
                            "strikePrice": 160,
                            "openInterest": 1800,
                            "changeinOpenInterest": 40,
                            "underlyingValue": 24200.5,
                        },
                    },
                ],
            }
        }


class AnalysisServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AnalysisService(FakeNseClient())

    def test_get_symbols(self) -> None:
        symbols = self.service.get_symbols()
        self.assertIn("NIFTY", symbols["indices"])

    def test_analyze_once(self) -> None:
        result = self.service.analyze_once(
            AnalysisInput(
                mode=OptionMode.INDEX,
                symbol="NIFTY",
                expiry_date="10-Apr-2026",
                strike_price=120,
            )
        )
        self.assertEqual(result.call_sum, 0.0)
        self.assertEqual(result.put_sum, 0.1)
        self.assertEqual(result.oi_signal, "Bullish")


if __name__ == "__main__":
    unittest.main()
