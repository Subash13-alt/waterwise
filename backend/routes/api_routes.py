"""
WaterWise ML v2 – API Routes
New endpoints: /api/sse, /api/heatmap, /api/budget, /api/health, /api/notes
"""
import json
import time
from flask import Blueprint, jsonify, request, Response, stream_with_context
from datetime import datetime, timedelta
from models import Zone, WaterReading, Alert, ZoneBudget, ZoneNote, HealthScore
from extensions import db
from sqlalchemy import func

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ── Flow ──────────────────────────────────────────────────────────────────────
@api_bp.route("/flow/<int:zone_id>")
def flow_data(zone_id):
    limit    = request.args.get("limit", 60, type=int)
    readings = (WaterReading.query.filter_by(zone_id=zone_id)
                .order_by(WaterReading.timestamp.desc()).limit(limit).all())
    readings.reverse()
    return jsonify([r.to_dict() for r in readings])


@api_bp.route("/flow/all")
def flow_all():
    zones  = Zone.query.filter_by(is_active=True).all()
    result = []
    for zone in zones:
        last = (WaterReading.query.filter_by(zone_id=zone.id)
                .order_by(WaterReading.timestamp.desc()).first())
        if last:
            d = last.to_dict()
            d["zone_name"] = zone.name
            d["baseline"]  = zone.baseline_flow_rate
            result.append(d)
    return jsonify(result)


# ── Stats ─────────────────────────────────────────────────────────────────────
@api_bp.route("/stats")
def stats():
    now    = datetime.utcnow()
    cutoff = now - timedelta(hours=24)
    return jsonify({
        "total_zones":          Zone.query.filter_by(is_active=True).count(),
        "active_alerts":        Alert.query.filter_by(is_resolved=False).count(),
        "total_consumption_kl": round(float(
            db.session.query(func.sum(WaterReading.total_volume))
            .filter(WaterReading.timestamp >= cutoff).scalar() or 0) / 1000, 2),
        "anomaly_count":  WaterReading.query.filter(
            WaterReading.timestamp >= cutoff, WaterReading.is_anomaly == True).count(),
        "normal_count":   WaterReading.query.filter(
            WaterReading.timestamp >= cutoff, WaterReading.is_anomaly == False).count(),
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
    })


# ── Alerts ────────────────────────────────────────────────────────────────────
@api_bp.route("/alerts")
def get_alerts():
    limit    = request.args.get("limit", 20, type=int)
    unres    = request.args.get("unresolved", "true").lower() == "true"
    zone_id  = request.args.get("zone_id", type=int)
    severity = request.args.get("severity")
    q        = Alert.query
    if unres:     q = q.filter_by(is_resolved=False)
    if zone_id:   q = q.filter_by(zone_id=zone_id)
    if severity:  q = q.filter_by(severity=severity)
    return jsonify([a.to_dict() for a in q.order_by(Alert.timestamp.desc()).limit(limit).all()])


@api_bp.route("/alerts/history")
def alert_history():
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    zone_id  = request.args.get("zone_id", type=int)
    severity = request.args.get("severity")
    atype    = request.args.get("type")
    q        = Alert.query
    if zone_id:  q = q.filter_by(zone_id=zone_id)
    if severity: q = q.filter_by(severity=severity)
    if atype:    q = q.filter_by(alert_type=atype)
    total    = q.count()
    alerts   = q.order_by(Alert.timestamp.desc()).offset((page-1)*per_page).limit(per_page).all()
    return jsonify({"total": total, "page": page, "per_page": per_page,
                    "alerts": [a.to_dict() for a in alerts]})


@api_bp.route("/alerts/<int:alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id):
    from alert_engine import resolve_alert as _res
    return jsonify({"success": _res(alert_id)})


# ── Consumption ───────────────────────────────────────────────────────────────
@api_bp.route("/consumption/zones")
def zone_consumption():
    cutoff = datetime.utcnow() - timedelta(hours=24)
    result = []
    for zone in Zone.query.filter_by(is_active=True).all():
        vol  = (db.session.query(func.sum(WaterReading.total_volume))
                .filter(WaterReading.zone_id==zone.id, WaterReading.timestamp>=cutoff).scalar() or 0)
        anom = WaterReading.query.filter(
            WaterReading.zone_id==zone.id, WaterReading.timestamp>=cutoff,
            WaterReading.is_anomaly==True).count()
        result.append({"zone_id": zone.id, "zone_name": zone.name,
                        "consumption_l": round(float(vol), 2), "anomaly_count": anom})
    return jsonify(result)


# ── Prediction ────────────────────────────────────────────────────────────────
@api_bp.route("/prediction/all")
def prediction_all():
    from ml_model import get_model
    return jsonify([
        {"zone_id": z.id, "zone_name": z.name, **get_model(z.id).predict_usage()}
        for z in Zone.query.filter_by(is_active=True).all()
    ])


# ── Heatmap (NEW) ─────────────────────────────────────────────────────────────
@api_bp.route("/heatmap")
def heatmap():
    zone_id = request.args.get("zone_id", type=int)
    from utils import anomaly_heatmap
    matrix = anomaly_heatmap(zone_id)
    return jsonify({"matrix": matrix,
                    "days": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
                    "hours": list(range(24))})


# ── Budget (NEW) ──────────────────────────────────────────────────────────────
@api_bp.route("/budget")
def budget():
    from utils import budget_progress
    zone_id = request.args.get("zone_id", type=int)
    return jsonify(budget_progress(zone_id))


@api_bp.route("/budget/set", methods=["POST"])
def set_budget():
    data    = request.get_json()
    zone_id = data.get("zone_id")
    litres  = data.get("budget_litres")
    month   = data.get("month", datetime.utcnow().strftime("%Y-%m"))
    thresh  = data.get("alert_threshold", 0.85)
    if not zone_id or not litres:
        return jsonify({"success": False, "error": "zone_id and budget_litres required"}), 400
    Zone.query.get_or_404(zone_id)
    existing = ZoneBudget.query.filter_by(zone_id=zone_id, month=month).first()
    if existing:
        existing.budget_litres   = litres
        existing.alert_threshold = thresh
    else:
        db.session.add(ZoneBudget(zone_id=zone_id, month=month,
                                  budget_litres=litres, alert_threshold=thresh))
    db.session.commit()
    return jsonify({"success": True})


# ── Health Score (NEW) ────────────────────────────────────────────────────────
@api_bp.route("/health")
def health_scores():
    zones  = Zone.query.filter_by(is_active=True).all()
    result = []
    for zone in zones:
        latest = (HealthScore.query.filter_by(zone_id=zone.id)
                  .order_by(HealthScore.timestamp.desc()).first())
        trend  = (HealthScore.query.filter_by(zone_id=zone.id)
                  .order_by(HealthScore.timestamp.desc()).limit(12).all())
        trend.reverse()
        result.append({
            "zone_id": zone.id, "zone_name": zone.name,
            "score":  latest.score if latest else 100.0,
            "grade":  latest.grade if latest else "A",
            "trend":  [h.to_dict() for h in trend],
        })
    return jsonify(result)


# ── Notes (NEW) ───────────────────────────────────────────────────────────────
@api_bp.route("/notes/<int:zone_id>")
def get_notes(zone_id):
    notes = (ZoneNote.query.filter_by(zone_id=zone_id)
             .order_by(ZoneNote.pinned.desc(), ZoneNote.created_at.desc()).all())
    return jsonify([n.to_dict() for n in notes])


@api_bp.route("/notes", methods=["POST"])
def add_note():
    data = request.get_json()
    Zone.query.get_or_404(data.get("zone_id"))
    note = ZoneNote(zone_id=data["zone_id"], content=data.get("content", ""),
                    author=data.get("author", "Operator"),
                    pinned=data.get("pinned", False))
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict())


@api_bp.route("/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    note = ZoneNote.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return jsonify({"success": True})


# ── Demo ──────────────────────────────────────────────────────────────────────
@api_bp.route("/demo/inject_leak/<int:zone_id>", methods=["POST"])
def inject_leak(zone_id):
    Zone.query.get_or_404(zone_id)
    from simulator import simulate_leak
    simulate_leak(zone_id)
    return jsonify({"success": True, "message": f"Leak injected for zone {zone_id} (30 s)"})


# ── Analytics ─────────────────────────────────────────────────────────────────
@api_bp.route("/analytics/top_loss")
def top_loss():
    from utils import get_top_loss_zones
    return jsonify([{"zone_id": d["zone"].id, "zone_name": d["zone"].name,
        "excess_volume_l": d["excess_volume"], "anomaly_count": d["anomaly_count"],
        "anomaly_pct": d["anomaly_pct"], "financial_loss_inr": d["financial_loss"]}
        for d in get_top_loss_zones()])


@api_bp.route("/analytics/monthly")
def monthly():
    from utils import monthly_summary
    return jsonify(monthly_summary())


# ── SSE – Server-Sent Events (NEW) ────────────────────────────────────────────
@api_bp.route("/sse/live")
def sse_live():
    """
    Real-time event stream. The frontend subscribes once and receives
    push updates instead of polling every 5 s.
    """
    def _generate():
        last_reading_id = 0
        last_alert_id   = 0
        while True:
            try:
                with db.engine.connect() as conn:
                    pass  # just test connection
                # Latest readings across all zones
                readings = (WaterReading.query.filter(WaterReading.id > last_reading_id)
                            .order_by(WaterReading.timestamp.desc()).limit(10).all())
                if readings:
                    last_reading_id = readings[0].id
                    payload = json.dumps([r.to_dict() for r in readings])
                    yield f"event: readings\ndata: {payload}\n\n"

                # New alerts
                alerts = (Alert.query.filter(Alert.id > last_alert_id,
                                             Alert.is_resolved == False)
                          .order_by(Alert.timestamp.desc()).limit(5).all())
                if alerts:
                    last_alert_id = alerts[0].id
                    payload = json.dumps([a.to_dict() for a in alerts])
                    yield f"event: alerts\ndata: {payload}\n\n"

                # Heartbeat
                yield f"event: ping\ndata: {json.dumps({'ts': datetime.utcnow().isoformat()})}\n\n"

            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            time.sleep(5)

    return Response(stream_with_context(_generate()),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})


# ── CSV Export ────────────────────────────────────────────────────────────────
@api_bp.route("/export/csv")
def export_csv():
    from utils import export_readings_csv
    zone_id  = request.args.get("zone_id", type=int)
    csv_data = export_readings_csv(zone_id=zone_id)
    return Response(csv_data, mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=waterwise_export.csv"})