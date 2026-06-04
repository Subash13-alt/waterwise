import sys
import os
import subprocess

# ── Paths ─────────────────────────────────────────────────────────
ROOT_DIR     = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR  = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

# ── Force install every package using THIS python executable ──────
PACKAGES = [
    "flask",
    "flask-sqlalchemy",
    "sqlalchemy",
    "scikit-learn",
    "pandas",
    "numpy",
    "werkzeug",
]

print("[SETUP] Installing all packages into current Python...")
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "--quiet"] + PACKAGES
)
print("[SETUP] All packages ready.\n")

# ── Reload site-packages so newly installed modules are visible ───
import importlib
import site
importlib.reload(site)

# ── Add backend to path ────────────────────────────────────────────
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ── Environment variables for path resolution ──────────────────────
os.environ["WW_ROOT"]     = ROOT_DIR
os.environ["WW_FRONTEND"] = FRONTEND_DIR
os.environ["WW_BACKEND"]  = BACKEND_DIR

# ── Import and create app ──────────────────────────────────────────
from app import create_app
app = create_app()

# ── Start server ───────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*55)
    print("  WaterWise ML v2 - Smart Leak Detection System")
    print("="*55)
    print(f"  Dashboard -> http://localhost:5000")
    print(f"  Analytics -> http://localhost:5000/analytics")
    print(f"  Zones     -> http://localhost:5000/zones/")
    print(f"  Heatmap   -> http://localhost:5000/heatmap")
    print(f"  Budget    -> http://localhost:5000/budget")
    print(f"  Alerts    -> http://localhost:5000/alerts")
    print("="*55 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)