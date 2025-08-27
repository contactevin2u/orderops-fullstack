import importlib
from io import BytesIO
from PIL import Image

def test_save_pod_image_public_url(tmp_path, monkeypatch):
    monkeypatch.setenv('UPLOAD_DIR', str(tmp_path))
    monkeypatch.setenv('PUBLIC_BASE_URL', 'https://api.example.com')
    from app.utils import storage
    importlib.reload(storage)
    img = Image.new('RGB', (1, 1), color='white')
    buf = BytesIO()
    img.save(buf, format='JPEG')
    url = storage.save_pod_image(buf.getvalue())
    assert url.startswith('https://api.example.com/static/uploads/')
