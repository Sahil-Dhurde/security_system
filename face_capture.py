import cv2
import os

# Create directory to save your face images
save_dir = "my_face_data" 
os.makedirs(save_dir, exist_ok=True)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

count = 0
MAX_PHOTOS = 50  # We'll capture 50 photos of your face

print("=== FACE TRAINING DATA CAPTURE ===")
print("Look at the camera. Press SPACE to capture your face.")
print(f"We need {MAX_PHOTOS} photos. Press Q to quit early.\n")

while count < MAX_PHOTOS:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

    cv2.putText(frame, f"Photos captured: {count}/{MAX_PHOTOS}",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    cv2.putText(frame, "Press SPACE to capture | Q to quit",
                (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow("Capture Your Face", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord(' '):  # Space to capture
        if len(faces) == 0:
            print("No face detected! Make sure your face is visible.")
        else:
            for (x, y, w, h) in faces:
                face_img = gray[y:y+h, x:x+w]
                face_img = cv2.resize(face_img, (200, 200))
                filename = os.path.join(save_dir, f"face_{count}.jpg")
                cv2.imwrite(filename, face_img)
                count += 1
                print(f"Captured photo {count}/{MAX_PHOTOS}")

    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

if count > 0:
    print(f"\n✅ Done! {count} photos saved in '{save_dir}' folder.")
    print("Now run: python step2_train.py")
else:
    print("\n❌ No photos captured.")
