import os, numpy as np, cv2
from ultralytics import YOLO
from insightface.app import FaceAnalysis

CONF_THRES = float(os.getenv("CONF_THRES", "0.25"))
IMG_SIZE = int(os.getenv("IMG_SIZE", "640"))
COSINE_THRESHOLD = float(os.getenv("COSINE_THRESHOLD", "0.55"))

# --- โหลดโมเดล ---
DETECT_MODEL = os.getenv("DETECT_MODEL", "best.pt")  # หรือ yolo11n.pt / yolov8n-face.pt
yolo = YOLO(DETECT_MODEL)  # ใช้ GPU อัตโนมัติถ้ามี CUDA

# ArcFace (rec) 512-d
face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0, det_size=(IMG_SIZE, IMG_SIZE))  # ctx_id=0 = GPU

def detect_boxes(img_bgr: np.ndarray):
    res = yolo.predict(source=img_bgr, imgsz=IMG_SIZE, conf=CONF_THRES, verbose=False)[0]
    boxes = []
    if res.boxes is None: return boxes
    for b in res.boxes.xyxy.cpu().numpy().astype(int):
        x1,y1,x2,y2 = map(int, b.tolist())
        x1,y1 = max(0,x1), max(0,y1)
        x2,y2 = min(img_bgr.shape[1],x2), min(img_bgr.shape[0],y2)
        if x2>x1 and y2>y1:
            boxes.append((x1,y1,x2,y2))
    return boxes

def embed_face(face_bgr: np.ndarray) -> np.ndarray | None:
    # ใช้ rec model ของ insightface โดยตรง
    rec = face_app.models.get("recognition", None)
    if rec is None:
        return None
    face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
    feat = rec.get_embedding(face_rgb)  # (512,)
    if feat is None: return None
    feat = feat.astype("float32")
    feat /= (np.linalg.norm(feat) + 1e-6)  # L2 normalize
    return feat

def detect_and_embed(img_bgr: np.ndarray) -> np.ndarray | None:
    boxes = detect_boxes(img_bgr)
    if not boxes: return None
    # ใช้หน้าที่ใหญ่สุด
    areas = [(x2-x1)*(y2-y1) for (x1,y1,x2,y2) in boxes]
    x1,y1,x2,y2 = boxes[int(np.argmax(areas))]
    face = img_bgr[y1:y2, x1:x2]
    return embed_face(face)

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a,b) / (np.linalg.norm(a)*np.linalg.norm(b) + 1e-6))

def best_score(probe: np.ndarray, gallery: list[np.ndarray]) -> float:
    return max((cosine(probe, g) for g in gallery), default=0.0)
