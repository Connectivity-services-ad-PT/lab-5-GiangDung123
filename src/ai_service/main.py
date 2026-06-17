from fastapi import FastAPI
import os

from pydantic import BaseModel
from ai_service.detector import detect
from ai_service.models import (
    PredictionRequest,
    PredictionResponse,
    HealthResponse,
    Detection,
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

    # Kiểm tra có phát hiện người không
    person_detected = any(
        item["label"] == "person"
        for item in detections
    )

    payload = {
        "cameraId": "cam01",
        "personDetected": person_detected,
        "isAuthorized": False
    }

    # Gửi sang A6
    try:
        requests.post(
            "http://IP_A6:8000/vision",
            json=payload,
            timeout=3
        )
        print("Đã gửi dữ liệu sang A6")
    except Exception as e:
        print("Lỗi gửi A6:", e)

    return PredictionResponse(
        detections=[
            Detection(**item)
            for item in detections
        ],
        processing_ms=42
    )