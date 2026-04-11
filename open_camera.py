"""
simple_camera.py
================
Fullscreen security camera — opens your webcam in a fullscreen window
and draws Green / Yellow / Red zones on the live feed.

Requirements (only 1 package needed):
    pip install opencv-python

Run:
    python simple_camera.py

Controls:
    Q  — quit
    S  — save a snapshot manually
    F  — toggle fullscreen on/off
"""

import cv2
import os
import time
from datetime import datetime

# ── Settings ──────────────────────────────────────────────────────────────────
CAMERA_INDEX = 0          # 0 = built-in webcam | try 1 or 2 for external cameras
SNAPSHOT_DIR = "snapshots"

# Zone colours  (BGR format for OpenCV)
COLOR_GREEN  = (0,  180,   0)
COLOR_YELLOW = (0,  200, 200)
COLOR_RED    = (0,   0,  220)
COLOR_WHITE  = (255, 255, 255)

ZONE_ALPHA = 0.18         # transparency of the coloured zone bands


# ── Helpers ───────────────────────────────────────────────────────────────────
def draw_zones(frame):
    """Draw three vertical coloured bands and label them."""
    h, w = frame.shape[:2]
    third = w // 3

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0),         (third,     h), COLOR_GREEN,  -1)
    cv2.rectangle(overlay, (third, 0),     (third * 2, h), COLOR_YELLOW, -1)
    cv2.rectangle(overlay, (third * 2, 0), (w,         h), COLOR_RED,    -1)
    cv2.addWeighted(overlay, ZONE_ALPHA, frame, 1 - ZONE_ALPHA, 0, frame)

    cv2.line(frame, (third,     0), (third,     h), COLOR_WHITE, 2)
    cv2.line(frame, (third * 2, 0), (third * 2, h), COLOR_WHITE, 2)

    font  = cv2.FONT_HERSHEY_SIMPLEX
    scale = max(0.6, w / 1920)          # scale label size to frame width
    cv2.putText(frame, "SAFE ZONE",    (10,           40), font, scale, COLOR_WHITE, 2)
    cv2.putText(frame, "WARNING ZONE", (third + 10,   40), font, scale, COLOR_WHITE, 2)
    cv2.putText(frame, "DANGER ZONE",  (third*2 + 10, 40), font, scale, COLOR_WHITE, 2)

    return frame


def save_snapshot(frame):
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(SNAPSHOT_DIR, f"snapshot_{ts}.jpg")
    cv2.imwrite(filename, frame)
    print(f"Snapshot saved: {filename}")
    return filename


def draw_status_bar(frame, fps):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, h - 40), (w, h), (15, 15, 15), -1)
    txt = f"FPS: {fps:.1f}   |   S = save snapshot   |   F = toggle fullscreen   |   Q = quit"
    cv2.putText(frame, txt, (12, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_WHITE, 1)
    return frame


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Opening camera ...  (press Q to quit, S to snapshot, F to toggle fullscreen)")

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"\n  ERROR: Could not open camera (index {CAMERA_INDEX}).")
        print("  Try changing CAMERA_INDEX to 1 or 2 at the top of this file.\n")
        return

    # Request the highest resolution the camera supports
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    win_name = "Security Camera"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)

    # Start in true fullscreen
    cv2.setWindowProperty(win_name, cv2.WND_PROP_FULLSCREEN,
                          cv2.WINDOW_FULLSCREEN)

    is_fullscreen = True
    prev_time     = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Warning: failed to grab frame - retrying ...")
            continue

        # FPS
        now       = time.time()
        fps       = 1.0 / max(now - prev_time, 0.001)
        prev_time = now

        frame = draw_zones(frame)
        frame = draw_status_bar(frame, fps)

        cv2.imshow(win_name, frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            print("Quitting ...")
            break

        elif key == ord("s"):
            save_snapshot(frame)

        elif key == ord("f"):
            # Toggle fullscreen / windowed
            if is_fullscreen:
                cv2.setWindowProperty(win_name, cv2.WND_PROP_FULLSCREEN,
                                      cv2.WINDOW_NORMAL)
                cv2.resizeWindow(win_name, 1280, 720)
                is_fullscreen = False
                print("Switched to windowed mode")
            else:
                cv2.setWindowProperty(win_name, cv2.WND_PROP_FULLSCREEN,
                                      cv2.WINDOW_FULLSCREEN)
                is_fullscreen = True
                print("Switched to fullscreen mode")

    cap.release()
    cv2.destroyAllWindows()
    print("Camera closed.")


if __name__ == "__main__":
    main()