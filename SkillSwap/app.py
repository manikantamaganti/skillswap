"""
SkillSwap Production WSGI Application Entry Point
Supports both 'gunicorn app:app' and 'gunicorn wsgi:app'
"""
import os
import sys
import importlib.util
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

# Locate backend directory
backend_app_path = None
for sub in ["SkillSwap/backend/app.py", "backend/app.py", "SkillSwap/SkillSwap/backend/app.py"]:
    p = ROOT_DIR / sub
    if p.exists():
        backend_app_path = p
        if str(p.parent) not in sys.path:
            sys.path.insert(0, str(p.parent))
        break

if not backend_app_path:
    raise RuntimeError("Could not find SkillSwap backend/app.py")

spec = importlib.util.spec_from_file_location("skillswap_core", str(backend_app_path))
mod = importlib.util.module_from_spec(spec)
sys.modules["skillswap_core"] = mod
spec.loader.exec_module(mod)
app = mod.app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
