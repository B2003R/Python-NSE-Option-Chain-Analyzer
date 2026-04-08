import unittest
from pathlib import Path

from fastapi.responses import FileResponse, RedirectResponse

from nse_oca.api.app import STATIC_DIR, ui_dashboard, ui_index


class ApiUiRouteTests(unittest.TestCase):
    def test_ui_index_redirects_to_app(self) -> None:
        response = ui_index()
        self.assertIsInstance(response, RedirectResponse)
        self.assertEqual(response.headers.get("location"), "/app")

    def test_ui_dashboard_serves_index_file(self) -> None:
        response = ui_dashboard()
        self.assertIsInstance(response, FileResponse)

        response_path = Path(response.path)
        self.assertTrue(response_path.exists())
        self.assertEqual(response_path, STATIC_DIR / "index.html")


if __name__ == "__main__":
    unittest.main()
