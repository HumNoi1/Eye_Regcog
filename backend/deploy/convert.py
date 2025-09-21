from ultralytics import YOLO

# โหลดโมเดล .pt ที่คุณเทรนมา
model = YOLO("yolo11n.pt")   # เปลี่ยนเป็น path จริง

# export เป็น ONNX
model.export(format="onnx", opset=12, imgsz=640)  # ปรับ imgsz ให้ตรงกับที่ใช้เทรน เช่น 640