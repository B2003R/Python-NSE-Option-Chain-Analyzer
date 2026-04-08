from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from nse_oca.domain.models import OptionMode
from nse_oca.infrastructure.option_chain_parser import parse_expiry_dates


class NseApiClientError(RuntimeError):
    """Raised for transport, schema, or retry exhaustion errors."""


@dataclass(frozen=True)
class NseApiConfig:
    url_oc: str = "https://www.nseindia.com/option-chain"
    url_contract_info: str = "https://www.nseindia.com/api/option-chain-contract-info?symbol="
    url_index_data: str = "https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol={}&expiry={}"
    url_stock_data: str = "https://www.nseindia.com/api/option-chain-v3?type=Equity&symbol={}&expiry={}"
    url_symbols: str = "https://www.nseindia.com/api/underlying-information"
    url_update: str = "https://api.github.com/repos/VarunS2002/Python-NSE-Option-Chain-Analyzer/releases/latest"
    headers: Dict[str, str] = field(
        default_factory=lambda: {
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
            "accept-language": "en,gu;q=0.9,hi;q=0.8",
            "accept-encoding": "gzip, deflate, br",
        }
    )


class NseApiClient:
    def __init__(
        self,
        config: Optional[NseApiConfig] = None,
        timeout: int = 5,
        max_retries: int = 2,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.config = config or NseApiConfig()
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.cookies: Dict[str, str] = {}

    def close(self) -> None:
        self.session.close()

    def _refresh_cookies(self) -> None:
        response = self.session.get(
            self.config.url_oc,
            headers=self.config.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        self.cookies = dict(response.cookies)

    def _request_json(self, url: str) -> Dict[str, Any]:
        last_error: Optional[Exception] = None

        for _ in range(self.max_retries + 1):
            try:
                if not self.cookies:
                    self._refresh_cookies()

                response = self.session.get(
                    url,
                    headers=self.config.headers,
                    timeout=self.timeout,
                    cookies=self.cookies,
                )

                if response.status_code == 401:
                    self._refresh_cookies()
                    response = self.session.get(
                        url,
                        headers=self.config.headers,
                        timeout=self.timeout,
                        cookies=self.cookies,
                    )

                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise NseApiClientError("Unexpected non-dict payload from NSE API")
                return payload
            except (requests.RequestException, ValueError, NseApiClientError) as err:
                last_error = err
                self.cookies = {}

        raise NseApiClientError(f"Failed to fetch JSON payload from {url}") from last_error

    def fetch_symbols(self) -> Dict[str, List[str]]:
        payload = self._request_json(self.config.url_symbols)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise NseApiClientError("Invalid symbols payload: missing data object")

        index_list = data.get("IndexList", [])
        underlying_list = data.get("UnderlyingList", [])

        indices = [
            item["symbol"]
            for item in index_list
            if isinstance(item, dict) and isinstance(item.get("symbol"), str)
        ]
        stocks = [
            item["symbol"]
            for item in underlying_list
            if isinstance(item, dict) and isinstance(item.get("symbol"), str)
        ]

        if not indices and not stocks:
            raise NseApiClientError("Invalid symbols payload: no symbols found")

        return {"indices": indices, "stocks": stocks}

    def fetch_expiry_dates(self, symbol: str) -> List[str]:
        payload = self._request_json(f"{self.config.url_contract_info}{symbol}")
        expiry_dates = parse_expiry_dates(payload)
        if not expiry_dates:
            raise NseApiClientError(f"No expiry dates available for symbol {symbol}")
        return expiry_dates

    def fetch_option_chain(self, symbol: str, expiry: str, mode: OptionMode) -> Dict[str, Any]:
        if mode == OptionMode.INDEX:
            url = self.config.url_index_data.format(symbol, expiry)
        else:
            url = self.config.url_stock_data.format(symbol, expiry)

        payload = self._request_json(url)
        if "records" not in payload:
            raise NseApiClientError("Invalid option chain payload: missing records")
        return payload

    def fetch_latest_release_tag(self) -> str:
        payload = self._request_json(self.config.url_update)
        tag_name = payload.get("tag_name")
        if not isinstance(tag_name, str):
            raise NseApiClientError("Release API response did not include tag_name")
        return tag_name
