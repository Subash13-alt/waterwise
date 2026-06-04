"""
WaterWise ML v2 – Configuration
"""
import os

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR   = os.path.abspath(os.path.join(BASE_DIR, ".."))
FRONT_DIR  = os.path.join(ROOT_DIR, "frontend")


class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "waterwise-v2-secret-2024")
    DEBUG      = False

    # Paths
    TEMPLATE_FOLDER = os.path.join(FRONT_DIR, "templates")
    STATIC_FOLDER   = os.path.join(FRONT_DIR, "static")
    STATIC_URL_PATH = "/static"

    # Database (stored in backend/data/)
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'waterwise.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Simulation
    SIMULATION_INTERVAL_SECONDS = 5

    # Rule thresholds
    HIGH_FLOW_MULTIPLIER          = 1.8
    CONSECUTIVE_ABNORMAL_FOR_LEAK = 3
    NIGHT_HOURS                   = (22, 6)
    NIGHT_FLOW_THRESHOLD          = 0.3

    # ML
    ISOLATION_FOREST_CONTAMINATION = 0.08
    ISOLATION_FOREST_N_ESTIMATORS  = 100
    MIN_READINGS_TO_TRAIN          = 30

    # Financial
    COST_PER_1000_LITERS = 20          # ₹