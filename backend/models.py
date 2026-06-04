"""
WaterWise ML v2 – Database Models
New in v2:
  - ZoneBudget   → monthly water budget per zone
  - ZoneNote     → operator notes on zones
  - HealthScore  → composite zone health stored over time
"""
from datetime import datetime
from extensions import db


# ── Zone ─────────────────────────────────────────────────────────────────────
class Zone(db.Model):
    __tablename__ = "zones"

    id                   = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(100), nullable=False, unique=True)
    baseline_flow_rate   = db.Column(db.Float, nullable=False)
    expected_daily_usage = db.Column(db.Float, nullable=False)
    location_tag         = db.Column(db.String(80), default="")   # NEW: geo tag
    created_at           = db.Column(db.DateTime, default=datetime.utcnow)
    is_active            = db.Column(db.Boolean, default=True)

    readings      = db.relationship("WaterReading", backref="zone", lazy="dynamic", cascade="all, delete-orphan")
    alerts        = db.relationship("Alert",        backref="zone", lazy="dynamic", cascade="all, delete-orphan")
    budgets       = db.relationship("ZoneBudget",   backref="zone", lazy="dynamic", cascade="all, delete-orphan")
    notes         = db.relationship("ZoneNote",     backref="zone", lazy="dynamic", cascade="all, delete-orphan")
    health_scores = db.relationship("HealthScore",  backref="zone", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name,
            "baseline_flow_rate": self.baseline_flow_rate,
            "expected_daily_usage": self.expected_daily_usage,
            "location_tag": self.location_tag,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "is_active": self.is_active,
        }


# ── Water Reading ─────────────────────────────────────────────────────────────
class WaterReading(db.Model):
    __tablename__ = "water_readings"

    id            = db.Column(db.Integer, primary_key=True)
    zone_id       = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False)
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    flow_rate     = db.Column(db.Float, nullable=False)
    total_volume  = db.Column(db.Float, nullable=False)
    pressure      = db.Column(db.Float, default=0.0)
    is_anomaly    = db.Column(db.Boolean, default=False)
    anomaly_score = db.Column(db.Float,   default=0.0)
    label         = db.Column(db.String(20), default="Normal")

    def to_dict(self):
        return {
            "id": self.id, "zone_id": self.zone_id,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "flow_rate": round(self.flow_rate, 4),
            "total_volume": round(self.total_volume, 2),
            "pressure": round(self.pressure, 2),
            "is_anomaly": self.is_anomaly,
            "anomaly_score": round(self.anomaly_score, 4),
            "label": self.label,
        }


# ── Alert ─────────────────────────────────────────────────────────────────────
class Alert(db.Model):
    __tablename__ = "alerts"

    id          = db.Column(db.Integer, primary_key=True)
    zone_id     = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    alert_type  = db.Column(db.String(50), nullable=False)
    severity    = db.Column(db.String(20), default="Medium")
    message     = db.Column(db.Text, nullable=False)
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id, "zone_id": self.zone_id,
            "zone_name": self.zone.name if self.zone else "Unknown",
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "alert_type": self.alert_type, "severity": self.severity,
            "message": self.message, "is_resolved": self.is_resolved,
        }


# ── Zone Budget (NEW) ─────────────────────────────────────────────────────────
class ZoneBudget(db.Model):
    """Monthly water budget per zone in litres."""
    __tablename__ = "zone_budgets"

    id              = db.Column(db.Integer, primary_key=True)
    zone_id         = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False)
    month           = db.Column(db.String(7), nullable=False)   # "YYYY-MM"
    budget_litres   = db.Column(db.Float, nullable=False)
    alert_threshold = db.Column(db.Float, default=0.85)         # alert at 85% used
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "zone_id": self.zone_id,
            "month": self.month, "budget_litres": self.budget_litres,
            "alert_threshold": self.alert_threshold,
        }


# ── Zone Note (NEW) ───────────────────────────────────────────────────────────
class ZoneNote(db.Model):
    """Operator notes attached to a zone."""
    __tablename__ = "zone_notes"

    id         = db.Column(db.Integer, primary_key=True)
    zone_id    = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False)
    content    = db.Column(db.Text, nullable=False)
    author     = db.Column(db.String(60), default="Operator")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    pinned     = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id, "zone_id": self.zone_id,
            "content": self.content, "author": self.author,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
            "pinned": self.pinned,
        }


# ── Health Score (NEW) ────────────────────────────────────────────────────────
class HealthScore(db.Model):
    """
    Composite health score [0–100] computed every simulation tick.
    100 = perfectly normal, 0 = critical leak.
    """
    __tablename__ = "health_scores"

    id        = db.Column(db.Integer, primary_key=True)
    zone_id   = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    score     = db.Column(db.Float, default=100.0)
    grade     = db.Column(db.String(2), default="A")   # A B C D F

    def to_dict(self):
        return {
            "id": self.id, "zone_id": self.zone_id,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "score": round(self.score, 1), "grade": self.grade,
        }