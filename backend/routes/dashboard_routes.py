from flask import Blueprint, render_template
from datetime import datetime, timedelta
from models import Zone, WaterReading, Alert
from extensions import db
from sqlalchemy import func

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    total_zones   = Zone.query.filter_by(is_active=True).count()
    active_alerts = Alert.query.filter_by(is_resolved=False).count()
    cutoff        = datetime.utcnow() - timedelta(hours=24)

    total_consumption = (
        db.session.query(func.sum(WaterReading.total_volume))
        .filter(WaterReading.timestamp >= cutoff).scalar() or 0)

    anomaly_count = WaterReading.query.filter(
        WaterReading.timestamp >= cutoff, WaterReading.is_anomaly == True).count()
    total_readings = WaterReading.query.filter(
        WaterReading.timestamp >= cutoff).count()
    anomaly_pct = round(anomaly_count / total_readings * 100, 1) if total_readings else 0

    recent_alerts = (Alert.query.filter_by(is_resolved=False)
                     .order_by(Alert.timestamp.desc()).limit(10).all())

    zones = Zone.query.filter_by(is_active=True).all()
    zone_status = {}
    for zone in zones:
        last = (WaterReading.query.filter_by(zone_id=zone.id)
                .order_by(WaterReading.timestamp.desc()).first())
        if last and last.label in ("Leak Risk", "Anomaly"):
            zone_status[zone.id] = "danger"
        elif last and last.flow_rate > zone.baseline_flow_rate * 1.5:
            zone_status[zone.id] = "warning"
        else:
            zone_status[zone.id] = "safe"

    return render_template(
        "dashboard.html",
        total_zones=total_zones, active_alerts=active_alerts,
        total_consumption=round(total_consumption / 1000, 2),
        anomaly_pct=anomaly_pct, recent_alerts=recent_alerts,
        zones=zones, zone_status=zone_status)