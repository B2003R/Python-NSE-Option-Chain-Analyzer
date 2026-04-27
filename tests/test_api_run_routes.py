import unittest
from importlib import import_module
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from nse_oca.domain import OptionMode
from nse_oca.worker import SchedulerRunError

api_app = import_module("nse_oca.api.app")


class ApiRunRouteTests(unittest.TestCase):
    def test_start_run_returns_502_when_bootstrap_execution_fails(self) -> None:
        request = api_app.RunStartRequest(
            mode=OptionMode.INDEX,
            symbol="NIFTY",
            expiry_date="10-Apr-2026",
            strike_price=24000,
            interval_seconds=60,
            persist=True,
        )

        with patch.object(api_app, "scheduler_service") as mock_scheduler:
            mock_scheduler.start_run.side_effect = SchedulerRunError("upstream failed")

            with self.assertRaises(HTTPException) as ctx:
                api_app.start_run(request)

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(ctx.exception.detail, "upstream failed")

    def test_start_run_saves_settings_when_scheduler_starts(self) -> None:
        request = api_app.RunStartRequest(
            mode=OptionMode.INDEX,
            symbol="NIFTY",
            expiry_date="10-Apr-2026",
            strike_price=24000,
            interval_seconds=60,
            persist=True,
        )
        fake_status = {"running": True}

        fake_setting_repo = MagicMock()
        fake_session_cm = MagicMock()
        fake_session_cm.__enter__.return_value = MagicMock()
        fake_session_cm.__exit__.return_value = False

        with (
            patch.object(api_app, "scheduler_service") as mock_scheduler,
            patch.object(api_app, "get_session", return_value=fake_session_cm),
            patch.object(api_app, "SettingRepository", return_value=fake_setting_repo),
        ):
            mock_scheduler.start_run.return_value = fake_status
            response = api_app.start_run(request)

        self.assertEqual(response, fake_status)
        self.assertEqual(fake_setting_repo.upsert_setting.call_count, 6)


if __name__ == "__main__":
    unittest.main()
