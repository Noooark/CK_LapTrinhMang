"""Camera event metadata shared by the client and server."""

CAMERA_THRESHOLDS = {
    "CAMERA_NO_FACE": ("no_face_threshold_seconds", 10),
    "CAMERA_MULTIPLE_FACES": ("multiple_faces_threshold_seconds", 3),
    "CAMERA_DISCONNECTED": ("camera_disconnect_threshold_seconds", 5),
    "CAMERA_OBSTRUCTED": ("obstruction_threshold_seconds", 10),
}
CAMERA_RECOVERED = "CAMERA_RECOVERED"
CAMERA_PHONE_DETECTED = "CAMERA_PHONE_DETECTED"
PHONE_THRESHOLD_SECONDS = 2
CAMERA_EVENTS = {*CAMERA_THRESHOLDS, CAMERA_RECOVERED, CAMERA_PHONE_DETECTED}
