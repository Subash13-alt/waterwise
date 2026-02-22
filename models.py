from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Zone(db.Model):
    __tablename__ = "zones"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    expected_daily_usage = db.Column(db.Float, nullable=False)
    baseline_flow_rate = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    readings = db.relationship("FlowReading", back_populates="zone", cascade="all, delete-orphan")
    alerts = db.relationship("AlertLog", back_populates="zone", cascade="all, delete-orphan")


class FlowReading(db.Model):
    __tablename__ = "flow_readings"

    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    flow_rate = db.Column(db.Float, nullable=False)
    total_volume = db.Column(db.Float, nullable=False)
    simulated_leak = db.Column(db.Boolean, default=False, nullable=False)

    zone = db.relationship("Zone", back_populates="readings")


class AlertLog(db.Model):
    __tablename__ = "alert_logs"

    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    alert_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    resolved = db.Column(db.Boolean, default=False, nullable=False)

    zone = db.relationship("Zone", back_populates="alerts")


class MonthlySummary(db.Model):
    __tablename__ = "monthly_summaries"

    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(7), nullable=False, index=True)  # YYYY-MM
    zone_id = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False, index=True)
    consumption_liters = db.Column(db.Float, nullable=False)
    estimated_loss_liters = db.Column(db.Float, nullable=False)

    zone = db.relationship("Zone")
