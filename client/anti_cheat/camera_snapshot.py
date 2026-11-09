"""Encode one in-memory webcam frame off the Tk and camera threads."""
import base64
from io import BytesIO

from PIL import Image

from common.snapshots import MAX_HEIGHT, MAX_JPEG_BYTES, MAX_WIDTH


def encode_snapshot(frame):
    try:
        with Image.fromarray(frame) as image:
            image.thumbnail((MAX_WIDTH, MAX_HEIGHT))
            for quality in (75, 55, 35):
                with BytesIO() as output:
                    image.save(output, "JPEG", quality=quality)
                    if output.tell() <= MAX_JPEG_BYTES:
                        return base64.b64encode(output.getvalue()).decode("ascii")
    except (OSError, TypeError, ValueError):
        pass
    return None
