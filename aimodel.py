# import cv2
# from ultralytics import YOLO
# model = YOLO("yolov8n.pt")
# model.train(data="caratulas_dataset.yaml", epochs=50)
# def extract_frames(video_path, output_folder, fps=1):
#     cap = cv2.VideoCapture(video_path)
#     frame_count = 0
#     while cap.isOpened():
#         ret, frame = cap.read()
#         if not ret:
#             break
#         if frame_count % int(cap.get(cv2.CAP_PROP_FPS) / fps) == 0:
#             cv2.imwrite(f"{output_folder}/frame_{frame_count}.jpg", frame)
#         frame_count += 1
#     cap.release()

# extract_frames("video.mp4", "frames")
# def detect_artwork(frame):
#     results = model.predict(frame, conf=0.7)
#     for box in results[0].boxes:
#         if results[0].names[box.cls.item()] == "book":  # Ejemplo: usar clase "book" como proxy
#             x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
#             return frame[y1:y2, x1:x2]  # Recortar región detectada
#     return None
# def process_image(cropped_image):
#     # Redimensionar y normalizar
#     resized = cv2.resize(cropped_image, (224, 224))
#     gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
#     # Aplicar umbral o filtros para mejorar texto/contornos
#     _, processed = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
#     return processed