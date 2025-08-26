import os
import sys
import types
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("JWT_SECRET", "test")

fake_admin = types.ModuleType("firebase_admin")
fake_admin.auth = types.ModuleType("firebase_admin.auth")
fake_admin.credentials = types.ModuleType("firebase_admin.credentials")
fake_admin.initialize_app = lambda *a, **kw: None
fake_admin.auth.verify_id_token = lambda *a, **kw: {}
fake_admin.auth.create_user = lambda *a, **kw: types.SimpleNamespace(uid="stub")
fake_admin.credentials.Certificate = lambda data: data
sys.modules["firebase_admin"] = fake_admin
sys.modules["firebase_admin.auth"] = fake_admin.auth
sys.modules["firebase_admin.credentials"] = fake_admin.credentials
