import os
import uuid
from io import BytesIO

from PIL import Image, ImageOps
from firebase_admin import storage

MAX_SIDE = 1280
MAX_BYTES = 5 * 1024 * 1024
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")


def save_pod_image(file_bytes: bytes) -> str:
    if len(file_bytes) > MAX_BYTES:
        raise ValueError("Image too large")
    
    img = Image.open(BytesIO(file_bytes))
    img = ImageOps.exif_transpose(img)
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = BytesIO()
    img.save(out, format="JPEG", quality=70, optimize=True)
    processed_bytes = out.getvalue()
    
    name = f"{uuid.uuid4().hex}.jpg"
    
    # ONLY use Firebase Storage - no local fallback to save Render disk space
    if not FIREBASE_STORAGE_BUCKET:
        raise ValueError("FIREBASE_STORAGE_BUCKET environment variable is required")
    
    print(f"DEBUG: Using Firebase Storage bucket: {FIREBASE_STORAGE_BUCKET}")
    bucket = storage.bucket(FIREBASE_STORAGE_BUCKET)
    blob_path = f"pod-images/{name}"
    blob = bucket.blob(blob_path)
    print(f"DEBUG: Uploading to Firebase Storage path: {blob_path}")
    blob.upload_from_string(processed_bytes, content_type="image/jpeg")
    blob.make_public()
    public_url = blob.public_url
    print(f"DEBUG: Firebase Storage upload successful: {public_url}")
    return public_url
