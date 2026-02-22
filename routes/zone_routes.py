from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import Zone, db

zone_bp = Blueprint("zone", __name__, url_prefix="/zones")


@zone_bp.get("/")
def list_zones():
    zones = Zone.query.order_by(Zone.created_at.desc()).all()
    return render_template("zones.html", zones=zones)


@zone_bp.post("/add")
def add_zone():
    try:
        zone = Zone(
            name=request.form["name"].strip(),
            expected_daily_usage=float(request.form["expected_daily_usage"]),
            baseline_flow_rate=float(request.form["baseline_flow_rate"]),
        )
        db.session.add(zone)
        db.session.commit()
        flash("Zone added successfully.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Failed to add zone: {exc}", "danger")
    return redirect(url_for("zone.list_zones"))


@zone_bp.post("/<int:zone_id>/edit")
def edit_zone(zone_id: int):
    zone = Zone.query.get_or_404(zone_id)
    try:
        zone.name = request.form["name"].strip()
        zone.expected_daily_usage = float(request.form["expected_daily_usage"])
        zone.baseline_flow_rate = float(request.form["baseline_flow_rate"])
        db.session.commit()
        flash("Zone updated successfully.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Failed to update zone: {exc}", "danger")
    return redirect(url_for("zone.list_zones"))


@zone_bp.post("/<int:zone_id>/delete")
def delete_zone(zone_id: int):
    zone = Zone.query.get_or_404(zone_id)
    try:
        db.session.delete(zone)
        db.session.commit()
        flash("Zone deleted.", "warning")
    except Exception as exc:
        db.session.rollback()
        flash(f"Failed to delete zone: {exc}", "danger")
    return redirect(url_for("zone.list_zones"))
