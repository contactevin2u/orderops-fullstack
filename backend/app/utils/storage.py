import os
import uuid
from io import BytesIO

from PIL import Image, ImageOps

MAX_SIDE = 1280
MAX_BYTES = 5 * 1024 * 1024
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_pod_image(file_bytes: bytes) -> str:
    if len(file_bytes) > MAX_BYTES:
        raise ValueError("Image too large")
    img = Image.open(BytesIO(file_bytes))
    img = ImageOps.exif_transpose(img)
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = BytesIO()
    img.save(out, format="JPEG", quality=70, optimize=True)
    name = f"{uuid.uuid4().hex}.jpg"
    path = os.path.join(UPLOAD_DIR, name)
    with open(path, "wb") as f:
        f.write(out.getvalue())
    return f"/static/uploads/{name}"
