import os
import uuid
from io import BytesIO

from PIL import Image, ImageOps
from firebase_admin import storage

MAX_SIDE = 1280
MAX_BYTES = 5 * 1024 * 1024
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")

# Create uploads directory for local development
if not FIREBASE_STORAGE_BUCKET:
    os.makedirs(UPLOAD_DIR, exist_ok=True)


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
    
    # Use Firebase Storage for production
    if FIREBASE_STORAGE_BUCKET:
        print(f"DEBUG: Using Firebase Storage bucket: {FIREBASE_STORAGE_BUCKET}")
        try:
            bucket = storage.bucket(FIREBASE_STORAGE_BUCKET)
            blob_path = f"pod-images/{name}"
            blob = bucket.blob(blob_path)
            print(f"DEBUG: Uploading to Firebase Storage path: {blob_path}")
            blob.upload_from_string(processed_bytes, content_type="image/jpeg")
            blob.make_public()
            public_url = blob.public_url
            print(f"DEBUG: Firebase Storage upload successful: {public_url}")
            return public_url
        except Exception as e:
            # Fallback to local storage if Firebase fails
            print(f"ERROR: Firebase storage failed, falling back to local: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("DEBUG: FIREBASE_STORAGE_BUCKET not set, using local storage")
    
    # Local storage fallback for development or Firebase failure
    path = os.path.join(UPLOAD_DIR, name)
    with open(path, "wb") as f:
        f.write(processed_bytes)
    return f"/static/uploads/{name}"
