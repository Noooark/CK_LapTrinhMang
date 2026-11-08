"""Local face counting using OpenCV's bundled frontal Haar cascade."""
from os import getenv


class FaceDetector:
    def __init__(self, cv):
        self.cv = cv
        self.minimum_brightness = self._threshold("QUIZ_CAMERA_MIN_BRIGHTNESS", 35)
        self.minimum_contrast = self._threshold("QUIZ_CAMERA_MIN_CONTRAST", 9)
        self.cascade = cv.CascadeClassifier(cv.data.haarcascades + "haarcascade_frontalface_default.xml")
        if self.cascade.empty():
            raise RuntimeError("OpenCV face cascade is unavailable")

    @staticmethod
    def _threshold(name, default):
        try:
            value = int(getenv(name, str(default)))
        except ValueError:
            return default
        return value if 0 <= value <= 255 else default

    def observe(self, frame):
        gray = self.cv.cvtColor(frame, self.cv.COLOR_BGR2GRAY)
        mean, deviation = self.cv.meanStdDev(gray)
        if mean.item() < self.minimum_brightness or deviation.item() < self.minimum_contrast:
            return "CAMERA_OBSTRUCTED", None
        faces = self.cascade.detectMultiScale(
            self.cv.equalizeHist(gray), scaleFactor=1.1, minNeighbors=5, minSize=(32, 32),
        )
        count = len(faces)
        if count == 0:
            return "CAMERA_NO_FACE", 0
        if count > 1:
            return "CAMERA_MULTIPLE_FACES", count
        return None, count
