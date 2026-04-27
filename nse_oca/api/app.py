from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from nse_oca.application import AnalysisInput, AnalysisService, AnalysisServiceError
from nse_oca.domain import OptionMode
from nse_oca.infrastructure import NseApiClient
from nse_oca.persistence import SettingRepository, SnapshotRepository, get_session, init_db
from nse_oca.worker import AnalysisScheduler, ScheduledRunConfig, SchedulerRunError

app = FastAPI(
    title="NSE Option Chain Analyzer API",
    version="0.1.0",
    description="Server bootstrap for the SOLID rewrite of NSE Option Chain Analyzer.",
)

API_DIR = Path(__file__).resolve().parent
STATIC_DIR = API_DIR / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

client = NseApiClient()
analysis_service = AnalysisService(client)
scheduler_service = AnalysisScheduler(analysis_service)


class AnalyzeRequest(BaseModel):
    mode: OptionMode = Field(description="Index or Stock mode")
    symbol: str = Field(min_length=1)
    expiry_date: str = Field(min_length=1)
    strike_price: int = Field(gt=0)


class RunStartRequest(BaseModel):
    mode: OptionMode = Field(description="Index or Stock mode")
    symbol: str = Field(min_length=1)
    expiry_date: str = Field(min_length=1)
    strike_price: int = Field(gt=0)
    interval_seconds: int = Field(default=60, ge=60)
    persist: bool = Field(default=True)


class SettingRequest(BaseModel):
    value: str


@app.get("/", include_in_schema=False)
def ui_index() -> RedirectResponse:
    return RedirectResponse(url="/app")


@app.get("/app", include_in_schema=False)
def ui_dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.on_event("startup")
def _startup_app() -> None:
    init_db()
    scheduler_service.start()


@app.on_event("shutdown")
def _shutdown_client() -> None:
    scheduler_service.shutdown()
    client.close()


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "scheduler_running": scheduler_service.status()["running"],
    }


@app.get("/symbols")
def get_symbols() -> Dict[str, Any]:
    try:
        return analysis_service.get_symbols()
    except AnalysisServiceError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err


@app.get("/expiries")
def get_expiries(symbol: str = Query(min_length=1)) -> Dict[str, Any]:
    try:
        dates = analysis_service.get_expiry_dates(symbol)
    except AnalysisServiceError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err
    return {"symbol": symbol, "expiry_dates": dates}


@app.post("/analyze")
def analyze(request: AnalyzeRequest, persist: bool = Query(default=True)) -> Dict[str, Any]:
    try:
        result = analysis_service.analyze_once(
            AnalysisInput(
                mode=request.mode,
                symbol=request.symbol,
                expiry_date=request.expiry_date,
                strike_price=request.strike_price,
            )
        )
    except AnalysisServiceError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err

    snapshot_record = None
    if persist:
        with get_session() as session:
            snapshot_repository = SnapshotRepository(session)
            snapshot_record = snapshot_repository.save_analysis(
                request=AnalysisInput(
                    mode=request.mode,
                    symbol=request.symbol,
                    expiry_date=request.expiry_date,
                    strike_price=request.strike_price,
                ),
                analysis=result,
            )

    return {
        "analysis": asdict(result),
        "snapshot": snapshot_record,
    }


@app.post("/runs/start")
def start_run(request: RunStartRequest) -> Dict[str, Any]:
    try:
        status = scheduler_service.start_run(
            ScheduledRunConfig(
                mode=request.mode,
                symbol=request.symbol,
                expiry_date=request.expiry_date,
                strike_price=request.strike_price,
                interval_seconds=request.interval_seconds,
                persist=request.persist,
            )
        )
        with get_session() as session:
            setting_repository = SettingRepository(session)
            setting_repository.upsert_setting("run.mode", request.mode.value)
            setting_repository.upsert_setting("run.symbol", request.symbol)
            setting_repository.upsert_setting("run.expiry_date", request.expiry_date)
            setting_repository.upsert_setting("run.strike_price", str(request.strike_price))
            setting_repository.upsert_setting("run.interval_seconds", str(request.interval_seconds))
            setting_repository.upsert_setting("run.persist", str(request.persist))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except SchedulerRunError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err

    return status


@app.post("/runs/stop")
def stop_run() -> Dict[str, Any]:
    return scheduler_service.stop_run()


@app.post("/runs/trigger")
def trigger_run() -> Dict[str, Any]:
    return scheduler_service.run_once_now()


@app.get("/runs/status")
def run_status() -> Dict[str, Any]:
    return scheduler_service.status()


@app.get("/snapshots/latest")
def latest_snapshot(
    mode: OptionMode = Query(),
    symbol: str = Query(min_length=1),
    expiry_date: str = Query(min_length=1),
    strike_price: int = Query(gt=0),
) -> Optional[Dict[str, Any]]:
    with get_session() as session:
        snapshot_repository = SnapshotRepository(session)
        snapshot = snapshot_repository.get_latest(
            mode=mode.value,
            symbol=symbol,
            expiry_date=expiry_date,
            strike_price=strike_price,
        )
    return snapshot


@app.get("/snapshots/history")
def history_snapshots(
    mode: OptionMode = Query(),
    symbol: str = Query(min_length=1),
    expiry_date: str = Query(min_length=1),
    strike_price: int = Query(gt=0),
    since_created_at: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> Dict[str, Any]:
    since_dt: Optional[datetime] = None
    if since_created_at:
        try:
            normalized = since_created_at.replace("Z", "+00:00")
            since_dt = datetime.fromisoformat(normalized)
        except ValueError as err:
            raise HTTPException(status_code=422, detail="since_created_at must be an ISO-8601 datetime") from err

    with get_session() as session:
        snapshot_repository = SnapshotRepository(session)
        history = snapshot_repository.get_history(
            mode=mode.value,
            symbol=symbol,
            expiry_date=expiry_date,
            strike_price=strike_price,
            since_created_at=since_dt,
            limit=limit,
        )

    return {"items": history, "count": len(history)}


@app.get("/settings")
def get_settings() -> Dict[str, str]:
    with get_session() as session:
        setting_repository = SettingRepository(session)
        return setting_repository.list_settings()


@app.put("/settings/{key}")
def put_setting(key: str, request: SettingRequest) -> Dict[str, str]:
    with get_session() as session:
        setting_repository = SettingRepository(session)
        return setting_repository.upsert_setting(key=key, value=request.value)
