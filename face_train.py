import cv2
import numpy as np
import os
import pickle

print("=== TRAINING FACE RECOGNIZER ===\n")

data_dir = "my_face_data"

if not os.path.exists(data_dir):
    print(f"❌ Folder '{data_dir}' not found. Run step1_capture.py first!")
    exit()

images = []
labels = []

for filename in os.listdir(data_dir):
    if filename.endswith(".jpg"):
        img_path = os.path.join(data_dir, filename)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            images.append(img)
            labels.append(0)  # 0 = authorized (you)

if len(images) == 0:
    print("❌ No images found in folder. Run step1_capture.py first!")
    exit()

print(f"📸 Found {len(images)} training images...")

# Train LBPH Face Recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.train(images, np.array(labels))

# Save the trained model
recognizer.save("face_model.yml")
print("✅ Model trained and saved as 'face_model.yml'")
print("Now run: python step3_live.py")