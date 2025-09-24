---
title: Eye Detection API
emoji: 👁️
colorFrom: blue
colorTo: red
sdk: docker
sdk_version: python3.9
app_file: main.py
pinned: false
---

# Eye Detection API

API สำหรับตรวจจับตาโดยใช้ YOLO model. ส่งภาพมาแล้วได้ภาพที่มี bounding box กลับ.

## Usage

POST /process_frame ด้วย FormData ที่มี key 'file' เป็นภาพ JPEG.