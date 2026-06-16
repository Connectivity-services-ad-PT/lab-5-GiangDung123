from pydantic import BaseModel
from typing import List


class Detection(BaseModel):
    label: str
    confidence: float
    bbox: List[int]


class PredictionRequest(BaseModel):
    image: str


class PredictionResponse(BaseModel):
    detections: List[Detection]
    processing_ms: int


class HealthResponse(BaseModel):
    status: str
    service: str
    model: str
    version: str