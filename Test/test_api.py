# pip install requests pillow
import base64, requests
from pathlib import Path

API = "http://localhost:8000"
IMG_PATH = "3_jpg.rf.034e2624f209bde314dc2b957d6d16fd.jpg"  # เปลี่ยนเป็นรูปของคุณ (JPEG/PNG)

# 1) ขอ nonce
challenge = requests.post(f"{API}/auth/challenge").json()
nonce = challenge["nonce"]
print("nonce:", nonce)

# 2) แปลงรูปเป็น base64 (ไม่ต้องมี data URI prefix ก็ได้)
b64 = base64.b64encode(Path(IMG_PATH).read_bytes()).decode("utf-8")

# 3) ส่งยืนยัน
payload = {"image_base64": b64, "nonce": nonce}
resp = requests.post(f"{API}/auth/verify-eye", json=payload)
print("status:", resp.status_code)
print("json:", resp.json())
