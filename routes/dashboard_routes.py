from datetime import datetime
from io import StringIO

import csv
from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import func

from alert_engine import compute_loss_analytics
from models import AlertLog, FlowReading, MonthlySummary, Zone, db


dashboard_bp = Blueprint("dashboard", __name__)


def _require_login():
    if not session.get("is_admin"):
        return redirect(url_for("dashboard.login"))
    return None


@dashboard_bp.get("/")
def home():
    guard = _require_login()
    if guard:
        return guard

    today = datetime.utcnow().date()
    total_zones = Zone.query.count()
    active_alerts = AlertLog.query.filter_by(resolved=False).count()
    daily_consumption = (
        db.session.query(func.coalesce(func.sum(FlowReading.total_volume), 0.0))
        .filter(func.date(FlowReading.timestamp) == today)
        .scalar()
    )

    consumption_by_zone = (
        db.session.query(Zone.name, func.coalesce(func.sum(FlowReading.total_volume), 0.0).label("consumption"))
        .outerjoin(FlowReading, Zone.id == FlowReading.zone_id)
        .filter((func.date(FlowReading.timestamp) == today) | (FlowReading.id.is_(None)))
        .group_by(Zone.id)
        .all()
    )

    latest_alert_zone_ids = {
        alert.zone_id
        for alert in AlertLog.query.filter_by(resolved=False)
        .order_by(AlertLog.timestamp.desc())
        .limit(20)
        .all()
    }
    alert_zone_names = {zone.name for zone in Zone.query.filter(Zone.id.in_(latest_alert_zone_ids)).all()} if latest_alert_zone_ids else set()

    recent_alerts = AlertLog.query.order_by(AlertLog.timestamp.desc()).limit(10).all()

    return render_template(
        "dashboard.html",
        total_zones=total_zones,
        active_alerts=active_alerts,
        daily_consumption=daily_consumption,
        consumption_by_zone=consumption_by_zone,
        latest_alert_zone_ids=latest_alert_zone_ids,
        alert_zone_names=alert_zone_names,
        recent_alerts=recent_alerts,
    )


@dashboard_bp.get("/api/flow-trends")
def flow_trends():
    points = (
        db.session.query(Zone.name, FlowReading.timestamp, FlowReading.flow_rate)
        .join(Zone, Zone.id == FlowReading.zone_id)
        .order_by(FlowReading.timestamp.desc())
        .limit(60)
        .all()
    )
    payload = [
        {"zone": zone_name, "timestamp": ts.isoformat(), "flow_rate": flow}
        for zone_name, ts, flow in reversed(points)
    ]
    return jsonify(payload)


@dashboard_bp.post("/simulate-leak/<int:zone_id>")
def simulate_leak(zone_id: int):
    guard = _require_login()
    if guard:
        return guard

    simulator = current_app.extensions.get("water_simulator")
    if simulator:
        simulator.simulate_leak(zone_id)
    return redirect(url_for("dashboard.home"))


@dashboard_bp.get("/analytics")
def analytics():
    guard = _require_login()
    if guard:
        return guard

    data = compute_loss_analytics()
    top3 = data[:3]
    financial_loss = sum(item["estimated_loss"] for item in data) / 1000 * current_app.config["COST_PER_1000_LITERS_INR"]

    month = datetime.utcnow().strftime("%Y-%m")
    monthly_rows = MonthlySummary.query.filter_by(month=month).all()
    if not monthly_rows:
        for item in data:
            row = MonthlySummary(
                month=month,
                zone_id=item["zone"].id,
                consumption_liters=item["usage"],
                estimated_loss_liters=item["estimated_loss"],
            )
            db.session.add(row)
        db.session.commit()
        monthly_rows = MonthlySummary.query.filter_by(month=month).all()

    return render_template(
        "analytics.html",
        top3=top3,
        financial_loss=financial_loss,
        monthly_rows=monthly_rows,
    )


@dashboard_bp.get("/analytics/export")
def export_analytics():
    month = datetime.utcnow().strftime("%Y-%m")
    rows = MonthlySummary.query.filter_by(month=month).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["month", "zone", "consumption_liters", "estimated_loss_liters"])
    for row in rows:
        writer.writerow([row.month, row.zone.name if row.zone else row.zone_id, row.consumption_liters, row.estimated_loss_liters])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=waterwise_{month}.csv"},
    )


@dashboard_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == current_app.config["ADMIN_USERNAME"] and password == current_app.config["ADMIN_PASSWORD"]:
            session["is_admin"] = True
            return redirect(url_for("dashboard.home"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@dashboard_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard.login"))
