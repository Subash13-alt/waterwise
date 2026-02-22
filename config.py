import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///waterwise.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Simulation settings
    SIMULATION_INTERVAL_SECONDS = int(os.getenv("SIMULATION_INTERVAL_SECONDS", "5"))
    NIGHT_USAGE_MULTIPLIER = float(os.getenv("NIGHT_USAGE_MULTIPLIER", "1.4"))

    # Alert rules
    HIGH_RISK_MULTIPLIER = 1.8
    LEAK_CONSECUTIVE_THRESHOLD = 3
    COST_PER_1000_LITERS_INR = 20

    # Email (console fallback if disabled)
    SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() == "true"
    SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    ALERT_FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", "waterwise-alerts@example.com")
    ALERT_TO_EMAIL = os.getenv("ALERT_TO_EMAIL", "admin@example.com")

    # Basic auth
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
