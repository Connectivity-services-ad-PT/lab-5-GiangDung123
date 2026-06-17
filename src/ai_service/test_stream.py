import cv2

url = "http://172.20.10.3:8000/video/stream"

cap = cv2.VideoCapture(url)

while True:
    ret, frame = cap.read()

    if not ret:
        print("Không đọc được frame")
        break

    cv2.imshow("A2 Camera Stream", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()