import cv2

print("Checking available cameras...")
for i in range(10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"Camera {i} is available")
        ret, frame = cap.read()
        if ret:
            print(f"  - Can read frames from camera {i}")
        else:
            print(f"  - Cannot read frames from camera {i}")
        cap.release()
    else:
        print(f"Camera {i} is not available")