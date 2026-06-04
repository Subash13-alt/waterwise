"""
WaterWise ML v2 – Alert Engine
Rule-based + ML + Budget alerts
"""
import logging
from datetime import datetime, timedelta
from config import Config
from extensions import db

logger = logging.getLogger(__name__)
_consecutive: dict = {}


def _recent(zone_id, atype, minutes=5):
    from models import Alert
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    return Alert.query.filter(
        Alert.zone_id == zone_id, Alert.alert_type == atype,
        Alert.timestamp >= cutoff, Alert.is_resolved == False).count() > 0


def _fire(zone_id, atype, severity, message):
    if _recent(zone_id, atype): return
    from models import Alert
    db.session.add(Alert(zone_id=zone_id, alert_type=atype, severity=severity, message=message))
    db.session.commit()
    logger.warning("[ALERT] zone=%d %s", zone_id, atype)


def evaluate_reading(reading, zone):
    zid, flow, baseline = zone.id, reading.flow_rate, zone.baseline_flow_rate
    hour = reading.timestamp.hour

    # Rule 1: high flow
    if flow > baseline * Config.HIGH_FLOW_MULTIPLIER:
        _consecutive[zid] = _consecutive.get(zid, 0) + 1
        _fire(zid, "High Flow", "High",
              f"Flow {flow:.2f} L/s > threshold {baseline*Config.HIGH_FLOW_MULTIPLIER:.2f} L/s.")
    else:
        _consecutive[zid] = 0

    # Rule 2: consecutive → leak
    if _consecutive.get(zid, 0) >= Config.CONSECUTIVE_ABNORMAL_FOR_LEAK:
        _fire(zid, "Leak Detected", "Critical",
              f"{_consecutive[zid]} consecutive high-flow readings in '{zone.name}'.")
        _consecutive[zid] = 0

    # Rule 3: night
    ns, ne = Config.NIGHT_HOURS
    if (hour >= ns or hour < ne) and flow > Config.NIGHT_FLOW_THRESHOLD:
        _fire(zid, "Night Usage", "Medium",
              f"Flow {flow:.2f} L/s at {hour:02d}:00 (night hours).")

    # ML labels
    if reading.label == "Leak Risk":
        _fire(zid, "High Risk", "Critical",
              f"ML HIGH RISK – score {reading.anomaly_score:.3f}, flow {flow:.2f} L/s.")
    elif reading.label == "Anomaly":
        _fire(zid, "ML Anomaly", "Medium",
              f"Isolation Forest anomaly – score {reading.anomaly_score:.3f}.")

    # Budget alert
    _check_budget(zone)


def _check_budget(zone):
    """Fire alert if zone has consumed >= alert_threshold of monthly budget."""
    from models import ZoneBudget, WaterReading
    month = datetime.utcnow().strftime("%Y-%m")
    budget = ZoneBudget.query.filter_by(zone_id=zone.id, month=month).first()
    if not budget: return

    start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    from sqlalchemy import func
    used = db.session.query(func.sum(WaterReading.total_volume)).filter(
        WaterReading.zone_id == zone.id, WaterReading.timestamp >= start).scalar() or 0

    if used >= budget.budget_litres * budget.alert_threshold:
        pct = round(used / budget.budget_litres * 100, 1)
        _fire(zone.id, "Budget Alert", "High",
              f"Zone '{zone.name}' used {pct}% of {budget.budget_litres:,.0f} L monthly budget.")


def resolve_alert(alert_id):
    from models import Alert
    a = Alert.query.get(alert_id)
    if a and not a.is_resolved:
        a.is_resolved = True
        a.resolved_at = datetime.utcnow()
        db.session.commit()
        return True
    return False