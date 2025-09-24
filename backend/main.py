#uvicorn main:app --reload --host 0.0.0.0 --port 8000

import base64
import cv2
import io
import numpy as np
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
    model = YOLO("models/best.pt")

@app.post("/process_frame")
async def process_frame(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if model:
        results = model(frame)
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
