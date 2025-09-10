from typing import Optional, Tuple
import torch
from ultralytics import YOLO
import numpy as np
from ..config import settings

_model: YOLO | None = None
_device = None

def load_model() -> None:
    global _model, _device
    # เลือก device
    if torch.cuda.is_available():
        if isinstance(settings.CUDA_DEVICE, str) and settings.CUDA_DEVICE.isdigit():
            device_index = int(settings.CUDA_DEVICE)
        else:
            device_index = 0
        _device = f"cuda:{device_index}"
    else:
        _device = "cpu"

    _model = YOLO(settings.YOLO_MODEL_PATH)
    # หมายเหตุ: Ultralytics จะเลือก device เองตอน predict ด้วยพารามิเตอร์ device




def predict_identity(image_rgb: np.ndarray) -> Tuple[Optional[str], Optional[float]]:
    """
    สมมติว่าโมเดลเป็นแบบ classify/face-id ที่คืน probs ให้เราเลือก top-1
    ถ้าเป็น detect-only ให้คุณปรับส่วนนี้ตามโมเดลจริง (เช่น crop eyes/face แล้วค่อย classify)
    """
    if _model is None:
        raise RuntimeError("Model not loaded")

    # ปรับพารามิเตอร์ตามโมเดลจริงของคุณ
    results = _model.predict(
        source=image_rgb,
        conf=settings.CONF_THRESHOLD,
        device=_device,
        verbose=False
    )


    r = results[0]
    # เคสที่เป็น classification
    if hasattr(r, 'probs') and r.probs is not None:
        probs = r.probs.data.cpu().numpy()
        top_idx = int(probs.argmax())
        conf = float(probs[top_idx])
        label = r.names[top_idx]
        return label, conf


    # เคสที่เป็น detection: หาคลาสที่ความเชื่อมั่นสูงสุด (สมมติคลาส = identity)
    if hasattr(r, 'boxes') and r.boxes is not None and len(r.boxes) > 0:
        # เอากล่อง conf สูงสุด
        best = r.boxes.conf.cpu().numpy().argmax()
        cls_idx = int(r.boxes.cls.cpu().numpy()[best])
        conf = float(r.boxes.conf.cpu().numpy()[best])
        label = r.names[cls_idx]
        return label, conf


    return None, None