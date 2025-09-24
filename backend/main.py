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


@app.post("/start_camera")
async def start_camera():
    global camera_active, cap
    if not camera_active:
        cap = cv2.VideoCapture(1)
        if cap.isOpened():
            camera_active = True
            return {"status": "started"}
        else:
            return {"status": "failed to open camera"}
    return {"status": "camera already active"}

@app.post("/stop_camera")
async def stop_camera():
    global camera_active, cap
    if camera_active and cap:
        cap.release()
        camera_active = False
        return {"status": "stopped"}
    return {"status": "camera not active"}

def generate_frames():
    global cap, model
    while camera_active and cap and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Run YOLO detection if model is loaded
        if model:
            results = model(frame)
            # Annotate frame with detections
            frame = results[0].plot()

    success, buffer = cv2.imencode(".jpg", annotated_frame)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode processed frame")

    encoded_image = base64.b64encode(buffer).decode("utf-8")
    return {"processed_image": encoded_image}


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Eye Detection API"}
