import cv2
import numpy as np

# Open the default camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

# Set camera resolution to maximum
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# Create full screen window
window_name = "Camera Zones"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# Transparency of overlay (0 = invisible, 1 = fully opaque)
ALPHA = 0.35

# Colors in BGR
GREEN  = (0, 200, 0)
YELLOW = (0, 200, 200)
RED    = (0, 0, 200)

print("Camera running. Press 'Q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to grab frame.")
        break

    h, w = frame.shape[:2]

    # Equal vertical thirds
    zone1_end = w // 3          # Green zone ends here
    zone2_end = 2 * (w // 3)   # Yellow zone ends here
    # Red zone goes to end of frame

    # Create overlay
    overlay = frame.copy()

    # Green zone (left)
    cv2.rectangle(overlay, (0, 0), (zone1_end, h), GREEN, -1)

    # Yellow zone (middle)
    cv2.rectangle(overlay, (zone1_end, 0), (zone2_end, h), YELLOW, -1)

    # Red zone (right)
    cv2.rectangle(overlay, (zone2_end, 0), (w, h), RED, -1)

    # Blend overlay with original frame
    frame = cv2.addWeighted(overlay, ALPHA, frame, 1 - ALPHA, 0)

    # Add zone labels (vertically centered)
    label_style = dict(fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1.4,
                       thickness=2, lineType=cv2.LINE_AA)

    cv2.putText(frame, "GREEN ZONE",  (zone1_end // 2 - 80, h // 2),
                color=(255, 255, 255), **label_style)
    cv2.putText(frame, "YELLOW ZONE", (zone1_end + (zone2_end - zone1_end) // 2 - 100, h // 2),
                color=(255, 255, 255), **label_style)
    cv2.putText(frame, "RED ZONE",    (zone2_end + (w - zone2_end) // 2 - 70, h // 2),
                color=(255, 255, 255), **label_style)

    # Draw vertical divider lines
    cv2.line(frame, (zone1_end, 0), (zone1_end, h), (255, 255, 255), 2)
    cv2.line(frame, (zone2_end, 0), (zone2_end, h), (255, 255, 255), 2)

    cv2.imshow(window_name, frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()