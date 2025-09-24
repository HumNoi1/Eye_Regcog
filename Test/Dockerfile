# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ไลบรารีระบบที่ OpenCV ต้องใช้
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsm6 libxext6 libgl1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ติดตั้ง dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ดเข้าอิมเมจ
COPY . .

EXPOSE 8000

# รัน uvicorn ตามที่คุณใช้ในคอมเมนต์ไฟล์
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]