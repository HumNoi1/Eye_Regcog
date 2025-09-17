import os
import time
import threading
from typing import Optional, List, Dict, Any, Tuple, Union
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

# =========================
# ตั้งค่าพื้นฐาน (แก้ได้ผ่าน ENV)
# =========================
MODEL_PATH      = os.getenv("MODEL_PATH", "models/best.pt")
CAMERA_DEVICE   = os.getenv("CAMERA_DEVICE", "/dev/video0")   # หรือ "0" สำหรับ webcam หลัก
CONF_THRES      = float(os.getenv("CONF_THRES", "0.5"))
IMG_SIZE        = int(os.getenv("IMG_SIZE", "640"))
DISPLAY_SCALE   = float(os.getenv("DISPLAY_SCALE", "1.0"))    # 1.0 = ไม่ย่อ
TARGET_FPS      = float(os.getenv("TARGET_FPS", "15"))        # FPS เป้าหมาย

# =========================
# โหลดโมเดล YOLO + GPU ถ้ามี
# =========================
try:
    from ultralytics import YOLO
    import torch
except Exception as e:
    raise RuntimeError(f"ต้องการ ultralytics + torch ให้ติดตั้งให้ครบก่อน: {e}")

DEVICE = 0 if torch.cuda.is_available() else "cpu"
model = YOLO(MODEL_PATH)

# warmup (ช่วยให้เฟรมแรก ๆ ลื่น)
try:
    dummy = np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)
    _ = model.predict(source=dummy, conf=CONF_THRES, device=DEVICE, imgsz=IMG_SIZE, verbose=False)
except Exception:
    pass

# =========================
# กล้อง + worker ประมวลผล
# =========================
def _parse_camera_device(cam: str) -> Union[int, str]:
    cam = str(cam)
    return int(cam) if cam.isdigit() else cam  # "0"->0, "/dev/video0"->path

class VideoWorker:
    """
    เปิดกล้อง, อ่านเฟรม, รัน YOLO, วาดกรอบ, เก็บเฟรมล่าสุด (annotated) + ผลตรวจจับล่าสุด
    ใช้ background thread เดียว ประหยัด GPU และแชร์ผลให้ทุก endpoint
    """
    def __init__(self, device: Union[str, int], conf_thres: float = 0.5, img_size: int = 640, target_fps: float = 15.0):
        self.cam_index = _parse_camera_device(str(device))
        self.conf_thres = conf_thres
        self.img_size = img_size
        self.target_fps = max(1.0, target_fps)

        self.cap: Optional[cv2.VideoCapture] = None
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()

        self.latest_annotated: Optional[np.ndarray] = None
        self.latest_dets: List[Dict[str, Any]] = []
        self.last_ts: float = 0.0
        self.started = False

    def start(self):
        if self.started:
            return
        self.stop_event.clear()
        self.cap = cv2.VideoCapture(self.cam_index)
        if not self.cap.isOpened():
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
            raise RuntimeError(f"ไม่สามารถเปิดกล้องได้: {self.cam_index}")

        # พยายามตั้งค่า FPS กล้อง (บางรุ่น/ไดรเวอร์อาจไม่รองรับ)
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.started = True

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = None
        self.thread = None
        self.started = False

    def _run(self):
        frame_interval = 1.0 / self.target_fps
        while not self.stop_event.is_set():
            start_t = time.time()
            if self.cap is None:
                break

            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            # ย่อเพื่อแสดงผล/ประหยัดแรง (ถ้าต้องการ)
            if DISPLAY_SCALE != 1.0:
                h, w = frame.shape[:2]
                frame = cv2.resize(frame, (int(w * DISPLAY_SCALE), int(h * DISPLAY_SCALE)))

            # รัน YOLO
            try:
                results = model.predict(
                    source=frame,
                    conf=self.conf_thres,
                    device=DEVICE,     # 0 = CUDA:0 ถ้ามี, ไม่มีก็ CPU
                    imgsz=self.img_size,
                    verbose=False
                )
                r = results[0]
                annotated = r.plot()  # วาดกรอบ + label + confidence

                # แปลงผลเป็น JSON-friendly
                dets: List[Dict[str, Any]] = []
                if getattr(r, "boxes", None) is not None and len(r.boxes) > 0:
                    xyxy = r.boxes.xyxy.cpu().numpy()
                    conf = r.boxes.conf.cpu().numpy()
                    cls  = r.boxes.cls.cpu().numpy().astype(int)
                    names = r.names
                    for i in range(len(xyxy)):
                        x1, y1, x2, y2 = xyxy[i].tolist()
                        dets.append({
                            "bbox_xyxy": [x1, y1, x2, y2],
                            "conf": float(conf[i]),
                            "cls": int(cls[i]),
                            "label": names.get(int(cls[i]), str(int(cls[i])))
                        })

                with self.lock:
                    self.latest_annotated = annotated
                    self.latest_dets = dets
                    self.last_ts = time.time()

            except Exception as e:
                print(f"[Worker] Inference error: {e}")

            # throttle ให้ใกล้ TARGET_FPS
            elapsed = time.time() - start_t
            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)

    def get_latest_annotated_jpeg(self) -> Optional[bytes]:
        with self.lock:
            if self.latest_annotated is None:
                return None
            ok, buf = cv2.imencode(".jpg", self.latest_annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                return None
            return buf.tobytes()

    def get_latest_dets(self) -> Tuple[List[Dict[str, Any]], float]:
        with self.lock:
            return list(self.latest_dets), self.last_ts


# worker ตัวเดียวแชร์ทั้งแอป
worker = VideoWorker(
    device=CAMERA_DEVICE,
    conf_thres=CONF_THRES,
    img_size=IMG_SIZE,
    target_fps=TARGET_FPS
)

# =========================
# FastAPI app + Lifespan + CORS
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    try:
        worker.start()
        print("[Startup] Video worker started.")
    except Exception as e:
        print(f"[Startup] ไม่สามารถเริ่มกล้องอัตโนมัติ: {e}")
    yield
    # shutdown
    try:
        worker.stop()
        print("[Shutdown] Video worker stopped.")
    except Exception:
        pass

app = FastAPI(title="Eye Recognition Stream API (YOLO + FastAPI)", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # แนะนำระบุโดเมน Next.js ของคุณเพื่อความปลอดภัย
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Pydantic models
# =========================
class Health(BaseModel):
    status: str
    device: Union[str, int]
    gpu: bool
    model_path: str

class DetsResponse(BaseModel):
    timestamp: float
    detections: List[Dict[str, Any]]

# =========================
# Endpoints
# =========================
@app.get("/health", response_model=Health)
def health():
    return Health(
        status="ok" if worker.started else "camera_not_started",
        device=worker.cam_index,
        gpu=torch.cuda.is_available(),
        model_path=MODEL_PATH
    )

@app.post("/start")
def start_camera():
    if worker.started:
        return {"message": "already started"}
    try:
        worker.start()
        return {"message": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
def stop_camera():
    if not worker.started:
        return {"message": "already stopped"}
    worker.stop()
    return {"message": "stopped"}

@app.get("/classes")
def classes():
    try:
        names = model.names if hasattr(model, "names") else {}
        return names
    except Exception:
        return {}

@app.get("/detections", response_model=DetsResponse)
def get_detections():
    dets, ts = worker.get_latest_dets()
    return DetsResponse(timestamp=ts, detections=dets)

@app.get("/frame.jpg")
def get_frame_jpg():
    """ดึงเฟรมปัจจุบัน (annotated) แบบภาพนิ่ง JPEG"""
    jpeg = worker.get_latest_annotated_jpeg()
    if jpeg is None:
        raise HTTPException(status_code=503, detail="ยังไม่มีเฟรมพร้อมใช้งาน")
    return Response(content=jpeg, media_type="image/jpeg")

@app.get("/stream")
def stream_mjpeg():
    """
    สตรีม MJPEG:
    ฝั่งเว็บใช้ <img src="http://<host>:8000/stream"> ก็ขึ้นภาพเคลื่อนไหวพร้อมกรอบ + confidence ได้
    """
    boundary = "frameboundary"
    def mjpeg_generator():
        while True:
            jpeg = worker.get_latest_annotated_jpeg()
            if jpeg is None:
                time.sleep(0.03)
                continue
            yield (
                b"--" + boundary.encode() + b"\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Cache-Control: no-cache\r\n"
                b"Pragma: no-cache\r\n"
                b"\r\n" + jpeg + b"\r\n"
            )
            time.sleep(max(0.0, 1.0 / TARGET_FPS))
    return StreamingResponse(mjpeg_generator(), media_type=f"multipart/x-mixed-replace; boundary=%s" % boundary)
