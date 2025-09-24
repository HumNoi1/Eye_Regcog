import cv2
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

camera_active = False
cap = None
model = None

@app.on_event("startup")
async def startup_event():
    global model
    model = YOLO('models/yolo11n.pt')

@app.post("/start_camera")
async def start_camera():
    global camera_active, cap
    if not camera_active:
        cap = cv2.VideoCapture(0)
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

        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type='multipart/x-mixed-replace; boundary=frame')

@app.get("/")
async def root():
    return {"message": "Eye Detection API"}