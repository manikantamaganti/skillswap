"""
Root WSGI Entry Point (delegates to SkillSwap/wsgi.py)
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SKILLSWAP_DIR = ROOT_DIR / "SkillSwap"
BACKEND_DIR = SKILLSWAP_DIR / "backend"

for d in [str(SKILLSWAP_DIR), str(BACKEND_DIR)]:
    if d not in sys.path:
        sys.path.insert(0, d)

from app import app

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

