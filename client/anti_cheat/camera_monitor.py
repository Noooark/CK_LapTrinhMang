"""A single webcam worker with a bounded preview and monotonic episode tracking."""
from dataclasses import dataclass
import logging
from threading import Event, Lock, Thread
from time import monotonic

from common.snapshots import SNAPSHOT_EVENTS
from common.camera import CAMERA_PHONE_DETECTED, CAMERA_RECOVERED, CAMERA_THRESHOLDS, PHONE_THRESHOLD_SECONDS
from client.anti_cheat.face_detector import FaceDetector
from client.anti_cheat.phone_detector import MODEL_PATH, PhoneDetector


DISCONNECTED = "CAMERA_DISCONNECTED"
PHONE_MAX_GAP_SECONDS = 1.5
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CameraSample:
    timestamp: float
    condition: str | None
    faces: int | None = None
    preview: object = None
    error: str | None = None
    device_index: int | None = None
    evidence: object = None
    phone_detected: bool | None = None


class CameraEpisodes:
    def __init__(self, settings):
        self.thresholds = {
            event: settings.get(key, default)
            for event, (key, default) in CAMERA_THRESHOLDS.items()
        }
        self.condition = None
        self.since = None
        self.alert = None
        self.phone_since = None
        self.phone_last_seen = None
        self.phone_clear_since = None
        self.phone_last_frame = None
        self.phone_reported = False

    def sample_phone(self, detected, timestamp):
        if detected is None:
            self.phone_since = self.phone_last_seen = self.phone_clear_since = None
            return None
        if timestamp == self.phone_last_frame:
            return None
        if self.phone_last_frame is not None and timestamp - self.phone_last_frame > PHONE_MAX_GAP_SECONDS:
            self.phone_since = self.phone_last_seen = self.phone_clear_since = None
        self.phone_last_frame = timestamp
        if not detected:
            if self.phone_clear_since is None:
                self.phone_clear_since = timestamp
            if timestamp - self.phone_clear_since >= 1:
                self.phone_reported = False
                self.phone_since = self.phone_last_seen = None
            return None
        self.phone_clear_since = None
        if self.phone_last_seen is None or timestamp - self.phone_last_seen > PHONE_MAX_GAP_SECONDS:
            self.phone_since = timestamp
        self.phone_last_seen = timestamp
        duration = timestamp - self.phone_since
        if not self.phone_reported and duration >= PHONE_THRESHOLD_SECONDS:
            self.phone_reported = True
            return CAMERA_PHONE_DETECTED, duration, None
        return None

    def sample(self, condition, faces, now):
        if self.since is None or self.condition != condition:
            self.condition, self.since = condition, now
        duration = now - self.since
        if condition is None:
            if self.alert and duration >= 1:
                self.alert = None
                return CAMERA_RECOVERED, None, None
        elif condition != self.alert and duration >= self.thresholds[condition]:
            self.alert = condition
            return condition, duration, faces if condition == "CAMERA_MULTIPLE_FACES" else None
        return None


class CameraMonitor:
    # Keep the device exclusive across a cancelled preview and a new preview.
    _device = Lock()

    def __init__(self, index=0, cv=None, detector_factory=FaceDetector, phone_model=MODEL_PATH):
        self.index = index
        self.cv = cv
        self.detector_factory = detector_factory
        self.phone_model = phone_model
        self.stopped = Event()
        self.finished = Event()
        self.changed = Event()
        self.preview = True
        self.evidence_enabled = False
        self.snapshot_consent = False
        self.phone_available = False
        self.latest = CameraSample(monotonic(), DISCONNECTED)
        self.thread = Thread(target=self._run, daemon=True, name="exam-camera")
        self.thread.start()

    def retry(self, index):
        if index != self.index or self.latest.condition == DISCONNECTED:
            self.index = index
            self.changed.set()

    def begin_exam(self):
        self.preview = False

    def stop(self):
        self.stopped.set()
        self.changed.set()

    def snapshot(self):
        sample = self.latest
        if (monotonic() - sample.timestamp > 2
                or (sample.device_index is not None and sample.device_index != self.index)):
            return CameraSample(sample.timestamp, DISCONNECTED, error=sample.error)
        return sample

    def _run(self):
        capture = None
        try:
            cv = self.cv
            if cv is None:
                import cv2 as cv
            detector = self.detector_factory(cv)
            phone = None
            if self.phone_model is not None and self.phone_model.is_file():
                try:
                    phone = PhoneDetector(cv, self.phone_model)
                    self.phone_available = True
                except (OSError, RuntimeError, cv.error):
                    logger.warning("Could not load the phone detection model")
            while not self.stopped.is_set():
                if self._device.acquire(timeout=0.2):
                    break
                self.latest = CameraSample(monotonic(), DISCONNECTED, error="Đang chờ giải phóng camera.")
            else:
                return
            try:
                while not self.stopped.is_set():
                    frame_started = monotonic()
                    if self.changed.is_set():
                        self.changed.clear()
                        if capture is not None:
                            capture.release()
                            capture = None
                    if capture is None:
                        device_index = self.index
                        capture = cv.VideoCapture(device_index)
                    ok, frame = capture.read() if capture.isOpened() else (False, None)
                    if self.stopped.is_set():
                        break
                    if not ok or frame is None:
                        self.latest = CameraSample(monotonic(), DISCONNECTED,
                                                   error="Không đọc được camera. Kiểm tra thiết bị và quyền truy cập.")
                        capture.release()
                        capture = None
                        self.changed.wait(2)
                        continue
                    height, width = frame.shape[:2]
                    phone_detected = None
                    if phone is not None:
                        try:
                            phone_detected = phone.sees_phone(frame)
                        except (RuntimeError, ValueError, IndexError, cv.error):
                            logger.warning("Phone detection stopped after an inference error")
                            phone = None
                            self.phone_available = False
                    if width > 480:
                        frame = cv.resize(frame, (480, max(1, height * 480 // width)))
                    condition, faces = detector.observe(frame)
                    evidence = self.evidence_enabled and (condition in SNAPSHOT_EVENTS or phone_detected)
                    rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB) if self.preview or evidence else None
                    self.latest = CameraSample(monotonic(), condition, faces,
                                               preview=rgb if self.preview else None,
                                               device_index=device_index,
                                               evidence=rgb if evidence else None,
                                               phone_detected=phone_detected)
                    self.changed.wait(max(0.03, 1 / 3 - (monotonic() - frame_started)))
            finally:
                try:
                    if capture is not None:
                        capture.release()
                finally:
                    self._device.release()
        except Exception as exc:
            # Treat native OpenCV/backend failures as unavailable camera.
            self.latest = CameraSample(monotonic(), DISCONNECTED,
                                       error=f"Không thể khởi chạy camera ({type(exc).__name__}). "
                                             "Kiểm tra OpenCV, thiết bị và quyền truy cập.")
        finally:
            self.finished.set()
