import base64
import io
import numpy as np
from PIL import Image

def base64_to_numpy(b64: str) -> np.ndarray:
    # ตัด prefix data URI ถ้ามี
    if ";base64," in b64:
        b64 = b64.split(",", 1)[1]
    img_bytes = base64.b64decode(b64)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return np.array(img)