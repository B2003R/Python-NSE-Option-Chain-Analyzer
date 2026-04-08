from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from nse_oca.domain import AnalysisResult, OptionMode, analyze_snapshot
from nse_oca.infrastructure import (
    NseApiClient,
    NseApiClientError,
    OptionChainParseError,
    parse_option_chain_snapshot,
)


class AnalysisServiceError(RuntimeError):
    """Raised when service-level analysis orchestration fails."""


@dataclass(frozen=True)
class AnalysisInput:
    mode: OptionMode
    symbol: str
    expiry_date: str
    strike_price: int


class AnalysisService:
    """Coordinates NSE fetch, payload normalization, and pure analysis."""

    def __init__(self, client: NseApiClient) -> None:
        self.client = client

    def get_symbols(self) -> Dict[str, List[str]]:
        try:
            return self.client.fetch_symbols()
        except NseApiClientError as err:
            raise AnalysisServiceError(str(err)) from err

    def get_expiry_dates(self, symbol: str) -> List[str]:
        try:
            return self.client.fetch_expiry_dates(symbol)
        except NseApiClientError as err:
            raise AnalysisServiceError(str(err)) from err

    def analyze_once(self, request: AnalysisInput) -> AnalysisResult:
        try:
            payload = self.client.fetch_option_chain(
                symbol=request.symbol,
                expiry=request.expiry_date,
                mode=request.mode,
            )
            snapshot = parse_option_chain_snapshot(payload, expiry_date=request.expiry_date)
            return analyze_snapshot(
                snapshot=snapshot,
                strike_price=request.strike_price,
                mode=request.mode,
            )
        except (NseApiClientError, OptionChainParseError, ValueError) as err:
            raise AnalysisServiceError(str(err)) from err
