#uvicorn main:app --reload --host 0.0.0.0 --port 8000

import base64
import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model: YOLO | None = None


@app.on_event("startup")
async def startup_event() -> None:
    """Load the YOLO model once when the application starts."""

    global model
    model = YOLO("models/best.pt")


@app.post("/process_frame")
async def process_frame(file: UploadFile = File(...)) -> dict[str, str]:
    """Receive a frame from the frontend, run detection and return the annotated image."""

    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty image data")

    np_frame = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(np_frame, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image data")

    results = model(frame)
    annotated_frame = results[0].plot()

    success, buffer = cv2.imencode(".jpg", annotated_frame)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode processed frame")

    encoded_image = base64.b64encode(buffer).decode("utf-8")
    return {"processed_image": encoded_image}


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Eye Detection API"}
