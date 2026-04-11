import cv2
import numpy as np
import os
import threading
import sys
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from collections import deque
from datetime import datetime

print("=== LIVE FACE RECOGNITION + ZONE DETECTION ===\n")

# =============================================================================
#  📧  EMAIL CONFIGURATION  — fill in your details here
# =============================================================================
EMAIL_ENABLED       = True               # Set False to disable email alerts

SENDER_EMAIL        = "sahildhurde@gmail.com"       # Gmail you send FROM
SENDER_PASSWORD     = "Sahildhurde@123"        # Gmail App Password (16 chars)
                                                    # Get one at:
                                                    # myaccount.google.com → Security
                                                    # → 2-Step Verification → App passwords

RECEIVER_EMAIL      = "sahildhurde@gmail.com"       # Who gets the alert email

EMAIL_SUBJECT       = "🚨 SECURITY ALERT — Unknown Person in Red Zone"
EMAIL_COOLDOWN_SEC  = 30   # seconds between emails (prevents inbox flooding)
# =============================================================================

if not os.path.exists("face_model.yml"):
    print("❌ Model not found! Run face_train.py first.")
    exit()
import cv2
import numpy as np
import os
import threading
import sys
import smtplib
import time
import math
import struct
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from collections import deque
from datetime import datetime

print("=== LIVE FACE RECOGNITION + ZONE DETECTION ===\n")

# =============================================================================
#  📧  EMAIL CONFIGURATION
# =============================================================================
EMAIL_ENABLED      = True
SENDER_EMAIL       = "sahildhurde@gmail.com"      # ← your Gmail address
SENDER_PASSWORD    = "nnln dsdo bjhp shgp"        # ← 16-char Gmail App Password
                                                  #   NOT your Gmail login password!
                                                  #   Get it: myaccount.google.com
                                                  #   → Security → App passwords
RECEIVER_EMAIL     = "sahildhurde@gmail.com"       # ← who receives the alert
EMAIL_SUBJECT      = "🚨 SECURITY ALERT — Unknown Person in Red Zone"
EMAIL_COOLDOWN_SEC = 30   # minimum seconds between emails
# =============================================================================

# =============================================================================
#  🔊  BUZZER CONFIGURATION
# =============================================================================
try:
    import pygame
    PYGAME_OK = True
except ImportError:
    PYGAME_OK = False

BUZZER_VOLUME  = 0.90
BUZZER_FREQ_LO = 600    # Hz — bottom of siren sweep
BUZZER_FREQ_HI = 1200   # Hz — top of siren sweep
BUZZER_SWEEP_S = 0.65   # seconds per half-sweep
# =============================================================================

# ── Load face model ───────────────────────────────────────────────────────────
if not os.path.exists("face_model.yml"):
    print("❌ Model not found! Run face_train.py first.")
    exit()

recognizer   = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("face_model.yml")
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
os.makedirs("snapshots", exist_ok=True)

# ── Stability buffer ──────────────────────────────────────────────────────────
BUFFER_SIZE          = 15
CONFIDENCE_THRESHOLD = 60
confidence_buffer    = deque(maxlen=BUFFER_SIZE)

# ── Email state ───────────────────────────────────────────────────────────────
last_email_time = 0
email_lock      = threading.Lock()


# =============================================================================
#  🔊  BUZZER — police siren (pygame) with WAV fallback
# =============================================================================
class Buzzer:
    SAMPLE_RATE   = 44100
    TREMOLO_HZ    = 8.0
    TREMOLO_DEPTH = 0.25

    def __init__(self):
        self._playing  = False
        self._stop_evt = threading.Event()
        self._thread   = None
        self._sound    = None
        self._pg_ok    = False
        self._init()

    def _init(self):
        if not PYGAME_OK:
            return
        try:
            pygame.mixer.pre_init(self.SAMPLE_RATE, -16, 1, 256)
            pygame.mixer.init()
            self._sound = self._build_siren()
            self._pg_ok = True
            print("🔊 Sound engine ready (police siren).")
        except Exception as e:
            print(f"pygame init failed: {e} — using fallback buzzer.")

    def _build_siren(self):
        total_s = BUZZER_SWEEP_S * 2
        n       = int(self.SAMPLE_RATE * total_s)
        t       = np.linspace(0.0, total_s, n, endpoint=False)

        tri    = 2.0 * np.abs(t / total_s - np.floor(t / total_s + 0.5))
        freq_t = BUZZER_FREQ_LO + (BUZZER_FREQ_HI - BUZZER_FREQ_LO) * tri
        phase  = 2.0 * math.pi * np.cumsum(freq_t) / self.SAMPLE_RATE

        wave = (1.00 * np.sin(phase) +
                0.40 * np.sin(2 * phase) +
                0.20 * np.sin(3 * phase) +
                0.10 * np.sin(4 * phase)) / 1.70

        tremolo = 1.0 - self.TREMOLO_DEPTH * (
            0.5 - 0.5 * np.cos(2 * math.pi * self.TREMOLO_HZ * t))
        wave *= tremolo * BUZZER_VOLUME

        fade = int(self.SAMPLE_RATE * 0.01)
        wave[:fade]  *= np.linspace(0, 1, fade)
        wave[-fade:] *= np.linspace(1, 0, fade)

        pcm = (wave * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(pcm)

    @staticmethod
    def _make_wav_bytes(freq=900, duration=0.4, rate=44100):
        n   = int(rate * duration)
        amp = 28000
        pcm = struct.pack(f"<{n}h",
              *[int(amp * math.sin(2 * math.pi * freq * i / rate))
                for i in range(n)])
        hdr = struct.pack("<4sI4s4sIHHIIHH4sI",
              b"RIFF", 36+len(pcm), b"WAVE", b"fmt ",
              16, 1, 1, rate, rate*2, 2, 16, b"data", len(pcm))
        return hdr + pcm

    def _fallback_beep(self):
        import tempfile, subprocess
        wav = self._make_wav_bytes()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav); fname = f.name
        try:
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(fname, winsound.SND_FILENAME)
            elif sys.platform == "darwin":
                subprocess.Popen(["afplay", fname]).wait()
            else:
                subprocess.Popen(["aplay", "-q", fname],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL).wait()
        finally:
            try: os.unlink(fname)
            except: pass

    def start(self):
        if self._playing:
            return
        self._stop_evt.clear()
        self._playing = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_evt.set()
        self._playing = False
        if self._pg_ok:
            try: pygame.mixer.stop()
            except: pass

    def _loop(self):
        if self._pg_ok:
            try:
                self._sound.play(loops=-1)
                while not self._stop_evt.is_set():
                    time.sleep(0.05)
                self._sound.stop()
                return
            except Exception:
                pass
        # fallback
        while not self._stop_evt.is_set():
            self._fallback_beep()
            for _ in range(6):
                if self._stop_evt.is_set(): return
                time.sleep(0.1)


# =============================================================================
#  📧  EMAIL SENDER
# =============================================================================
def send_alert_email(snapshot_path: str):
    def _send():
        global last_email_time
        with email_lock:
            now = time.time()
            if now - last_email_time < EMAIL_COOLDOWN_SEC:
                return
            last_email_time = now

        try:
            timestamp      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg            = MIMEMultipart()
            msg["From"]    = SENDER_EMAIL
            msg["To"]      = RECEIVER_EMAIL
            msg["Subject"] = EMAIL_SUBJECT

            body = f"""
⚠️  SECURITY ALERT ⚠️

An UNKNOWN person has entered the RED ZONE.

📅 Date & Time  : {timestamp}
📍 Zone         : RED (Danger Zone)
🔴 Status       : UNAUTHORIZED ACCESS DETECTED

A snapshot of the intruder is attached to this email.

— Automated Security System
"""
            msg.attach(MIMEText(body, "plain"))

            if snapshot_path and os.path.exists(snapshot_path):
                with open(snapshot_path, "rb") as f:
                    img_data = f.read()
                img_part = MIMEImage(img_data, name=os.path.basename(snapshot_path))
                img_part.add_header("Content-Disposition", "attachment",
                                    filename=os.path.basename(snapshot_path))
                msg.attach(img_part)

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

            print(f"📧 Alert email sent → {RECEIVER_EMAIL}  [{timestamp}]")

        except smtplib.SMTPAuthenticationError:
            print("❌ Email auth failed — use a Gmail App Password, not your login password.")
            print("   Get one: myaccount.google.com → Security → App passwords")
        except Exception as e:
            print(f"❌ Email error: {e}")

    threading.Thread(target=_send, daemon=True).start()


def save_snapshot(frame) -> str:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join("snapshots", f"intruder_{ts}.jpg")
    cv2.imwrite(path, frame)
    print(f"📸 Snapshot saved: {path}")
    return path


# =============================================================================
#  CAMERA SETUP
# =============================================================================
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Error: Could not open camera.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

window_name = "Security Camera"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

GREEN  = (0, 200,   0)
YELLOW = (0, 200, 200)
RED    = (0,   0, 200)
WHITE  = (255, 255, 255)
ALPHA  = 0.3

buzzer              = Buzzer()
last_message        = ""
email_snapshot_sent = False
tick                = 0

print("✅ System running. Press Q to quit.\n")
if EMAIL_ENABLED:
    print(f"📧 Email alerts → {RECEIVER_EMAIL}  (cooldown: {EMAIL_COOLDOWN_SEC}s)\n")

# =============================================================================
#  MAIN LOOP
# =============================================================================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    tick += 1
    h, w  = frame.shape[:2]

    zone1_end = w  // 3
    zone2_end = 2 * (w // 3)

    # ── Zone overlays ─────────────────────────────────────────────────────────
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0),         (zone1_end, h), GREEN,  -1)
    cv2.rectangle(overlay, (zone1_end, 0), (zone2_end, h), YELLOW, -1)
    cv2.rectangle(overlay, (zone2_end, 0), (w, h),         RED,    -1)
    frame = cv2.addWeighted(overlay, ALPHA, frame, 1 - ALPHA, 0)

    ls = dict(fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1.2,
              thickness=2, lineType=cv2.LINE_AA)
    cv2.putText(frame, "GREEN ZONE",  (20, 40),             color=WHITE, **ls)
    cv2.putText(frame, "YELLOW ZONE", (zone1_end + 20, 40), color=WHITE, **ls)
    cv2.putText(frame, "RED ZONE",    (zone2_end + 20, 40), color=WHITE, **ls)
    cv2.line(frame, (zone1_end, 0), (zone1_end, h), WHITE, 2)
    cv2.line(frame, (zone2_end, 0), (zone2_end, h), WHITE, 2)

    # ── Face detection ────────────────────────────────────────────────────────
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=7, minSize=(60, 60)
    )

    red_zone_alert = False

    for (x, y, fw, fh) in faces:
        face_gray          = cv2.resize(gray[y:y+fh, x:x+fw], (200, 200))
        label, confidence  = recognizer.predict(face_gray)

        confidence_buffer.append(confidence)
        avg_conf = sum(confidence_buffer) / len(confidence_buffer)

        # Warm-up phase
        if len(confidence_buffer) < BUFFER_SIZE // 2:
            cv2.rectangle(frame, (x, y), (x+fw, y+fh), (200, 200, 0), 2)
            cv2.putText(frame, "Identifying...", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 0), 2)
            continue

        is_authorized = avg_conf < CONFIDENCE_THRESHOLD
        identity      = "AUTHORIZED" if is_authorized else "UNKNOWN"
        box_color     = (0, 255, 0) if is_authorized else (0, 0, 255)

        cv2.rectangle(frame, (x, y), (x+fw, y+fh), box_color, 3)
        cv2.putText(frame, f"{identity} ({int(avg_conf)})",
                    (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, box_color, 2)

        face_cx = x + fw // 2
        if face_cx < zone1_end:   zone = "GREEN"
        elif face_cx < zone2_end: zone = "YELLOW"
        else:                     zone = "RED"

        if is_authorized:
            msgs = {
                "GREEN":  "✅ CLEAR    — Authorized in GREEN zone.",
                "YELLOW": "⚠️  WARNING  — Authorized in YELLOW zone.",
                "RED":    "🚨 CAUTION  — Authorized in RED zone."
            }
        else:
            msgs = {
                "GREEN":  "⚠️  WARNING  — UNKNOWN in GREEN zone!",
                "YELLOW": "🚨 DANGER   — UNKNOWN in YELLOW zone!",
                "RED":    "🚨 ALERT    — UNKNOWN in RED zone!"
            }
            if zone == "RED":
                red_zone_alert = True

        message = msgs[zone]
        if message != last_message:
            print(message)
            last_message = message

        cv2.putText(frame, message.split("—")[-1].strip(),
                    (x, y + fh + 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (255, 255, 0), 2)

    # Reset when no face is in frame
    if len(faces) == 0:
        confidence_buffer.clear()
        email_snapshot_sent = False

    # ── 🔊 Buzzer + 📧 Email on RED zone intrusion ────────────────────────────
    if red_zone_alert:
        buzzer.start()                                  # siren on (loops until stopped)
        if EMAIL_ENABLED and not email_snapshot_sent:
            snap = save_snapshot(frame.copy())
            send_alert_email(snap)
            email_snapshot_sent = True                  # one email per intrusion event
    else:
        buzzer.stop()                                   # siren off immediately

    # ── Flashing alarm banner ─────────────────────────────────────────────────
    if red_zone_alert and (tick % 20 < 10):
        cv2.rectangle(frame, (0, h - 65), (w, h), (0, 0, 200), -1)
        cv2.putText(frame,
                    "  🚨  UNKNOWN IN RED ZONE — BUZZER ON + EMAIL SENT  🚨",
                    (w // 2 - 400, h - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, WHITE, 3)

    cv2.imshow(window_name, frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ── Cleanup ───────────────────────────────────────────────────────────────────
buzzer.stop()
cap.release()
cv2.destroyAllWindows()
print("\nSystem stopped.")
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("face_model.yml")
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

os.makedirs("snapshots", exist_ok=True)

# ── Stability buffer ──────────────────────────────────────────────────────────
BUFFER_SIZE          = 15
CONFIDENCE_THRESHOLD = 60
confidence_buffer    = deque(maxlen=BUFFER_SIZE)

# ── Email state ───────────────────────────────────────────────────────────────
last_email_time  = 0        # epoch seconds of last sent email
email_lock       = threading.Lock()


# =============================================================================
#  EMAIL SENDER
# =============================================================================
def send_alert_email(snapshot_path: str):
    """
    Sends an email with:
      • Timestamp of intrusion
      • Snapshot image attached
    Runs in a daemon thread so it never blocks the video loop.
    """
    def _send():
        global last_email_time
        with email_lock:
            now = time.time()
            if now - last_email_time < EMAIL_COOLDOWN_SEC:
                return                          # still in cooldown
            last_email_time = now

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            msg = MIMEMultipart()
            msg["From"]    = SENDER_EMAIL
            msg["To"]      = RECEIVER_EMAIL
            msg["Subject"] = EMAIL_SUBJECT

            body = f"""
⚠️  SECURITY ALERT ⚠️

An UNKNOWN person has entered the RED ZONE.

📅 Date & Time : {timestamp}
📍 Zone        : RED (Danger Zone)
🔴 Status      : UNAUTHORIZED ACCESS DETECTED

A snapshot of the intruder is attached to this email.

— Security System
"""
            msg.attach(MIMEText(body, "plain"))

            # Attach snapshot image
            if snapshot_path and os.path.exists(snapshot_path):
                with open(snapshot_path, "rb") as f:
                    img_data = f.read()
                image = MIMEImage(img_data, name=os.path.basename(snapshot_path))
                image.add_header(
                    "Content-Disposition", "attachment",
                    filename=os.path.basename(snapshot_path)
                )
                msg.attach(image)

            # Send via Gmail SMTP (SSL)
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

            print(f"📧 Alert email sent to {RECEIVER_EMAIL}  [{timestamp}]")

        except smtplib.SMTPAuthenticationError:
            print("❌ Email auth failed — check SENDER_EMAIL and SENDER_PASSWORD.")
            print("   Make sure you're using a Gmail App Password, not your login password.")
        except Exception as e:
            print(f"❌ Email failed: {e}")

    threading.Thread(target=_send, daemon=True).start()


def save_snapshot(frame) -> str:
    """Save a JPEG snapshot and return its file path."""
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join("snapshots", f"intruder_{ts}.jpg")
    cv2.imwrite(path, frame)
    print(f"📸 Snapshot saved: {path}")
    return path


# =============================================================================
#  BEEP (audio alert)
# =============================================================================
def beep():
    def _beep():
        if sys.platform == "win32":
            import winsound
            for _ in range(3):
                winsound.Beep(1000, 300)
        elif sys.platform == "darwin":
            os.system("afplay /System/Library/Sounds/Sosumi.aiff")
        else:
            os.system(
                "beep -f 1000 -l 300 -r 3 2>/dev/null || "
                "paplay /usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga 2>/dev/null"
            )
    threading.Thread(target=_beep, daemon=True).start()


# =============================================================================
#  CAMERA SETUP
# =============================================================================
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Error: Could not open camera.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

window_name = "Security Camera"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

GREEN  = (0, 200, 0)
YELLOW = (0, 200, 200)
RED    = (0, 0, 200)
WHITE  = (255, 255, 255)
ALPHA  = 0.3

last_message   = ""
beep_cooldown  = 0
BEEP_INTERVAL  = 60
email_snapshot_sent = False   # prevent sending duplicate emails per intrusion event

print("✅ System running. Press Q to quit.\n")
if EMAIL_ENABLED:
    print(f"📧 Email alerts → {RECEIVER_EMAIL}  (cooldown: {EMAIL_COOLDOWN_SEC}s)\n")

# =============================================================================
#  MAIN LOOP
# =============================================================================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]

    zone1_end = w // 3
    zone2_end = 2 * (w // 3)

    # Draw zone overlays
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0),         (zone1_end, h), GREEN,  -1)
    cv2.rectangle(overlay, (zone1_end, 0), (zone2_end, h), YELLOW, -1)
    cv2.rectangle(overlay, (zone2_end, 0), (w, h),         RED,    -1)
    frame = cv2.addWeighted(overlay, ALPHA, frame, 1 - ALPHA, 0)

    ls = dict(fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1.2, thickness=2,
              lineType=cv2.LINE_AA)
    cv2.putText(frame, "GREEN ZONE",  (20, 40),             color=WHITE, **ls)
    cv2.putText(frame, "YELLOW ZONE", (zone1_end + 20, 40), color=WHITE, **ls)
    cv2.putText(frame, "RED ZONE",    (zone2_end + 20, 40), color=WHITE, **ls)

    cv2.line(frame, (zone1_end, 0), (zone1_end, h), WHITE, 2)
    cv2.line(frame, (zone2_end, 0), (zone2_end, h), WHITE, 2)

    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=7, minSize=(60, 60)
    )

    red_zone_alert = False

    for (x, y, fw, fh) in faces:
        face_gray = cv2.resize(gray[y:y+fh, x:x+fw], (200, 200))
        label, confidence = recognizer.predict(face_gray)

        confidence_buffer.append(confidence)
        avg_confidence = sum(confidence_buffer) / len(confidence_buffer)

        # Still warming up
        if len(confidence_buffer) < BUFFER_SIZE // 2:
            cv2.rectangle(frame, (x, y), (x+fw, y+fh), (200, 200, 0), 2)
            cv2.putText(frame, "Identifying...", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 0), 2)
            continue

        is_authorized = avg_confidence < CONFIDENCE_THRESHOLD
        identity      = "AUTHORIZED" if is_authorized else "UNKNOWN"
        box_color     = (0, 255, 0) if is_authorized else (0, 0, 255)

        cv2.rectangle(frame, (x, y), (x+fw, y+fh), box_color, 3)
        cv2.putText(frame, f"{identity} ({int(avg_confidence)})",
                    (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, box_color, 2)

        face_cx = x + fw // 2
        if face_cx < zone1_end:
            zone = "GREEN"
        elif face_cx < zone2_end:
            zone = "YELLOW"
        else:
            zone = "RED"

        if is_authorized:
            if zone == "GREEN":
                message = "✅ CLEAR     — Authorized person in GREEN zone."
            elif zone == "YELLOW":
                message = "⚠️  CRITICAL  — Authorized person in YELLOW zone."
            else:
                message = "🚨 DANGER    — Authorized person in RED zone."

        else:
            if zone == "GREEN":
                message = "⚠️  CRITICAL  — UNKNOWN person in GREEN zone!"
            elif zone == "YELLOW":
                message = "🚨 DANGER    — UNKNOWN person in YELLOW zone!"
            else:
                message = "🚨 DANGER    — UNKNOWN person in RED zone!"
                red_zone_alert = True

        if message != last_message:
            print(message)
            last_message = message

        cv2.putText(frame, message.split("—")[-1].strip(),
                    (x, y + fh + 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (255, 255, 0), 2)

    # Clear buffer when no face is visible
    if len(faces) == 0:
        confidence_buffer.clear()
        email_snapshot_sent = False   # reset — next intrusion will trigger email again

    # ── BEEP + EMAIL when unknown is in RED zone ──────────────────────────────
    if red_zone_alert:
        # Audio beep
        if beep_cooldown == 0:
            beep()
            beep_cooldown = BEEP_INTERVAL

        # Email with snapshot (once per intrusion event, then cooldown handles repeats)
        if EMAIL_ENABLED and not email_snapshot_sent:
            snapshot_path = save_snapshot(frame.copy())
            send_alert_email(snapshot_path)
            email_snapshot_sent = True   # don't spam every frame

    if beep_cooldown > 0:
        beep_cooldown -= 1
    # ─────────────────────────────────────────────────────────────────────────

    # ── Alarm banner at the bottom of screen ─────────────────────────────────
    if red_zone_alert and (beep_cooldown % 20 < 10):
        cv2.rectangle(frame, (0, h - 65), (w, h), (0, 0, 200), -1)
        banner = "  🚨  UNKNOWN IN RED ZONE — ALERT SENT  🚨"
        cv2.putText(frame, banner, (w // 2 - 320, h - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, WHITE, 3)
    # ─────────────────────────────────────────────────────────────────────────

    cv2.imshow(window_name, frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("\nSystem stopped.")