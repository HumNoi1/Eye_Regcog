#uvicorn main:app --reload --host 0.0.0.0 --port 8000

import cv2
import io
import numpy as np
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
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
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Loading model on device: {device}")
    model = YOLO("models/best.pt")
    model.to(device)

@app.post("/process_frame")
async def process_frame(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Resize if too large for speed optimization
    h, w = frame.shape[:2]
    if w > 1280 or h > 720:
        scale = min(1280 / w, 720 / h)
        new_w, new_h = int(w * scale), int(h * scale)
        frame = cv2.resize(frame, (new_w, new_h))
    
    if model:
        # Optimize for speed and accuracy
        results = model(frame, conf=0.7, iou=0.5, imgsz=640, half=torch.cuda.is_available())
        # Annotate frame with detections
        annotated_frame = results[0].plot()
        
        # Encode annotated frame to JPEG
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if ret:
            return StreamingResponse(io.BytesIO(buffer.tobytes()), media_type="image/jpeg")
        else:
            raise HTTPException(status_code=500, detail="Failed to encode image")
    else:
        raise HTTPException(status_code=500, detail="Model not loaded")

@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Eye Detection API"}
