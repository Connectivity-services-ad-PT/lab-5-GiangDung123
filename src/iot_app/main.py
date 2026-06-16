import os
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

import requests
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic import BaseModel, Field

# ================= CONFIG =================
SERVICE_NAME = os.getenv("SERVICE_NAME", "iot-ingestion")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

AI_SERVICE_URL = os.getenv(
    "AI_SERVICE_URL",
    "http://ai-service:9000"
)

# ===== Fail Fast =====
required_envs = {
    "AUTH_TOKEN": AUTH_TOKEN
}

missing = [k for k, v in required_envs.items() if not v]

if missing:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing)}"
    )

app = FastAPI(
    title="FIT4110 Lab 05 - IoT Ingestion Service",
    version=SERVICE_VERSION,
)

# ================= ENUM =================
class SensorMetric(str, Enum):
    temperature = "temperature"
    humidity = "humidity"
    motion = "motion"
    smoke = "smoke"


class SensorUnit(str, Enum):
    celsius = "celsius"
    percent = "percent"
    boolean = "boolean"
    ppm = "ppm"


# ================= MODELS =================
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class SensorReadingCreate(BaseModel):
    device_id: str = Field(..., min_length=3)
    metric: SensorMetric
    value: float = Field(..., ge=-40, le=80)
    unit: Optional[SensorUnit] = None
    timestamp: str


class SensorReading(BaseModel):
    reading_id: str
    device_id: str
    metric: SensorMetric
    value: float
    unit: Optional[SensorUnit]
    timestamp: str
    created_at: str


class SensorReadingCreated(BaseModel):
    reading_id: str
    device_id: str
    metric: SensorMetric
    accepted: bool
    created_at: str


# ================= MEMORY =================
READINGS: List[Dict] = []


# ================= UTIL =================
def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def next_reading_id():
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"R-{today}-{len(READINGS)+1:04d}"


def build_problem(status_code: int, title: str, detail: str, instance: str = None):
    return {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }


# ================= AUTH =================
def verify_bearer_token(
    authorization: Optional[str] = Header(default=None, convert_underscores=False)
):
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail=build_problem(
                401,
                "Unauthorized",
                "Missing Authorization header"
            ),
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=build_problem(
                401,
                "Unauthorized",
                "Invalid bearer format"
            ),
        )

    token = authorization.split(" ", 1)[1]

    if token != AUTH_TOKEN:
        raise HTTPException(
            status_code=401,
            detail=build_problem(
                401,
                "Unauthorized",
                "Invalid bearer token"
            ),
        )


# ================= ERROR HANDLERS =================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            media_type="application/problem+json",
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=build_problem(exc.status_code, "HTTP Error", str(exc.detail)),
        media_type="application/problem+json",
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    err = exc.errors()[0] if exc.errors() else {}

    loc = ".".join(map(str, err.get("loc", [])))
    msg = err.get("msg", "validation error")

    return JSONResponse(
        status_code=422,
        content=build_problem(
            422,
            "Validation error",
            f"{loc}: {msg}" if loc else msg,
            str(request.url.path),
        ),
        media_type="application/problem+json",
    )


# ================= ROOT =================

@app.get("/")
def root():
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "running",
        "ai_service": AI_SERVICE_URL
    }


# ================= HEALTH =================
@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
    )


# ================= AI HEALTH =================
@app.get("/ai/health")
def ai_health():
    try:
        r = requests.get(f"{AI_SERVICE_URL}/health", timeout=5)
        return r.json()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=build_problem(
                503,
                "AI Service Unavailable",
                str(e),
            ),
        )


# ================= CREATE =================
@app.post(
    "/readings",
    response_model=SensorReadingCreated,
    status_code=201,
    dependencies=[Depends(verify_bearer_token)],
)
def create_reading(payload: SensorReadingCreate, response: Response):

    if (
        payload.metric == SensorMetric.temperature
        and payload.value >= 70
    ):
        response.headers["X-Warning"] = "high-temperature"

    rid = next_reading_id()
    created_at = now_iso()

    READINGS.append({
        "reading_id": rid,
        "device_id": payload.device_id,
        "metric": payload.metric.value,
        "value": payload.value,
        "unit": payload.unit.value if payload.unit else None,
        "timestamp": payload.timestamp,
        "created_at": created_at,
    })

    return SensorReadingCreated(
        reading_id=rid,
        device_id=payload.device_id,
        metric=payload.metric,
        accepted=True,
        created_at=created_at,
    )


# ================= LATEST =================
@app.get(
    "/readings/latest",
    dependencies=[Depends(verify_bearer_token)],
)
def latest_readings(
    device_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
):

    items = READINGS

    if device_id:
        items = [i for i in items if i["device_id"] == device_id]

    return {
        "items": items[-limit:]
    }


# ================= GET BY ID =================
@app.get(
    "/readings/{reading_id}",
    dependencies=[Depends(verify_bearer_token)],
)
def get_reading(reading_id: str):

    for item in READINGS:
        if item["reading_id"] == reading_id:
            return item

    raise HTTPException(
        status_code=404,
        detail=build_problem(
            404,
            "Not Found",
            f"Reading {reading_id} not found",
            f"/readings/{reading_id}",
        ),
    )
from pydantic import BaseModel

class VisionRequest(BaseModel):
    image: str

@app.post("/vision", response_model=VisionResponse)
def vision(req: VisionRequest):

    try:

        response = requests.post(
            f"{AI_SERVICE_URL}/predict",
            json={
                "image": req.image
            },
            timeout=5
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as ex:

        raise HTTPException(
            status_code=503,
            detail=build_problem(
                503,
                "AI Service Unavailable",
                str(ex),
                "/vision"
            )
        )