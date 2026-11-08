"""Phone presence from the OpenCV Zoo YOLOX-S COCO ONNX model."""
from pathlib import Path


MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "object_detection_yolox_2022nov.onnx"
PHONE_CLASS = 67
MODEL_SIZE = 640
PHONE_MIN_SCORE = 0.35
CLOSE_PHONE_MIN_SCORE = 0.30
TILTED_PHONE_MIN_SCORE = 0.22


class PhoneDetector:
    def __init__(self, cv, path=MODEL_PATH):
        self.cv = cv
        self.net = cv.dnn.readNetFromONNX(str(path))

    def sees_phone(self, frame):
        import numpy as np

        resized = self._fit(frame, MODEL_SIZE)
        padded = np.full((MODEL_SIZE, MODEL_SIZE, 3), 114, dtype=np.uint8)
        padded[:resized.shape[0], :resized.shape[1]] = resized
        if self._detect(padded, PHONE_MIN_SCORE):
            return True

        aligned = self._deskew(frame)
        score = CLOSE_PHONE_MIN_SCORE if aligned is frame else TILTED_PHONE_MIN_SCORE
        if self._detect(self._rotation_grid(aligned), score):
            return True
        return self._detect(self._rotation_grid(self.cv.flip(aligned, 1)), score)

    def _fit(self, frame, size):
        height, width = frame.shape[:2]
        scale = size / max(height, width)
        return self.cv.resize(frame, (max(1, int(width * scale)), max(1, int(height * scale))))

    def _rotation_grid(self, frame):
        import numpy as np

        # Evaluate four orientations in one network pass.
        tile = MODEL_SIZE // 2
        grid = np.full((MODEL_SIZE, MODEL_SIZE, 3), 114, dtype=np.uint8)
        rotations = (None, self.cv.ROTATE_90_CLOCKWISE, self.cv.ROTATE_180, self.cv.ROTATE_90_COUNTERCLOCKWISE)
        for index, rotation in enumerate(rotations):
            view = frame if rotation is None else self.cv.rotate(frame, rotation)
            view = self._fit(view, tile)
            height, width = view.shape[:2]
            x = (index % 2) * tile + (tile - width) // 2
            y = (index // 2) * tile + (tile - height) // 2
            grid[y:y + height, x:x + width] = view
        return grid

    def _deskew(self, frame):
        import numpy as np

        height, width = frame.shape[:2]
        gray = self.cv.cvtColor(frame, self.cv.COLOR_BGR2GRAY)
        lines = self.cv.HoughLinesP(self.cv.Canny(gray, 35, 100), 1, np.pi / 180, 25,
                                   minLineLength=min(width, height) // 6, maxLineGap=8)
        if lines is None:
            return frame
        segments = lines[:, 0]
        dx = segments[:, 2] - segments[:, 0]
        dy = segments[:, 3] - segments[:, 1]
        lengths = np.hypot(dx, dy)
        angles = (np.degrees(np.arctan2(dy, dx)) + 45) % 90 - 45
        strongest = lengths.argmax()
        angle = angles[strongest]
        agreeing = np.abs((angles - angle + 45) % 90 - 45) <= 5
        if abs(angle) <= 5 or np.count_nonzero(agreeing & (lengths >= lengths[strongest] / 3)) < 2:
            return frame
        transform = self.cv.getRotationMatrix2D((width / 2, height / 2), float(angle), 1.2)
        return self.cv.warpAffine(frame, transform, (width, height), borderValue=(114, 114, 114))

    def _detect(self, image, minimum_score):
        import numpy as np

        self.net.setInput(self.cv.dnn.blobFromImage(image, swapRB=True))
        detections = self.net.forward()[0]
        # A single well-scored candidate is enough for presence. No boxes are saved.
        classes = detections[:, 5:]
        phone_scores = detections[:, 4] * classes[:, PHONE_CLASS]
        return bool(np.any((phone_scores >= minimum_score) & (classes.argmax(axis=1) == PHONE_CLASS)))
