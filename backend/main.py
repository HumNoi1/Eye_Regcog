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
    model = YOLO('models/best.pt')

@app.post("/start_camera")
async def start_camera():
    global camera_active, cap
    if not camera_active:
        # Try different camera indices with better error handling
        for camera_index in [0, 1, 2, 3]:
            try:
                print(f"Trying camera index {camera_index}")
                cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)  # Use V4L2 backend explicitly
                
                if cap.isOpened():
                    # Set camera properties for better performance
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    
                    # Test if camera actually works by reading a frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        camera_active = True
                        print(f"Camera opened successfully on index {camera_index}, frame shape: {frame.shape}")
                        return {"status": "started", "camera_index": camera_index}
                    else:
                        print(f"Camera {camera_index} opened but failed to read frame")
                        cap.release()
                        cap = None
                else:
                    print(f"Failed to open camera {camera_index}")
                    cap = None
            except Exception as e:
                print(f"Error with camera {camera_index}: {str(e)}")
                if cap:
                    cap.release()
                cap = None
        
        return {"status": "failed to open camera", "error": "No working camera found"}
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
            print("Failed to read frame from camera")
            break

        if frame is None:
            print("Frame is None")
            continue

        # Run YOLO detection if model is loaded
        if model:
            try:
                results = model(frame)
                # Annotate frame with detections
                frame = results[0].plot()
            except Exception as e:
                print(f"YOLO processing error: {e}")
                # Continue with original frame if YOLO fails

        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            print("Failed to encode frame")
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