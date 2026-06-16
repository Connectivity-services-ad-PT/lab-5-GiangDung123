from fastapi import FastAPI
from detector import detect
from pydantic import BaseModel
from models import (
    PredictionRequest,
    PredictionResponse,
    HealthResponse,
    Detection
)

app = FastAPI(
    title="AI Vision Service",
    version="0.1.0"
)
class PredictRequest(BaseModel):
    image: str

@app.get("/health", response_model=HealthResponse)
def health():

    return HealthResponse(
        status="ok",
        service="ai-vision",
        model="mock-yolov8",
        version="0.1.0"
    )
    


@app.get("/models")
def models():

    return {
        "current": "mock-yolov8",
        "available": [
            "mock-yolov8",
            "yolov8n",
            "mediapipe"
        ]
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(req: PredictionRequest):

    detections = detect(req.image)

    return PredictionResponse(
        detections=[
            Detection(**item)
            for item in detections
        ],
        processing_ms=42
    )