from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import Zone, ZoneNote, ZoneBudget
from extensions import db
from datetime import datetime

zone_bp = Blueprint("zones", __name__, url_prefix="/zones")


@zone_bp.route("/")
def list_zones():
    zones = Zone.query.order_by(Zone.created_at.desc()).all()
    return render_template("zones.html", zones=zones)


@zone_bp.route("/add", methods=["GET", "POST"])
def add_zone():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        baseline = request.form.get("baseline_flow_rate", type=float)
        daily    = request.form.get("expected_daily_usage", type=float)
        loc      = request.form.get("location_tag", "").strip()
        budget   = request.form.get("monthly_budget", type=float)
        if not name or baseline is None or daily is None:
            flash("All fields are required.", "danger")
            return redirect(url_for("zones.add_zone"))
        if Zone.query.filter_by(name=name).first():
            flash("Zone name already exists.", "warning")
            return redirect(url_for("zones.add_zone"))
        zone = Zone(name=name, baseline_flow_rate=baseline,
                    expected_daily_usage=daily, location_tag=loc)
        db.session.add(zone)
        db.session.commit()
        if budget:
            month = datetime.utcnow().strftime("%Y-%m")
            db.session.add(ZoneBudget(zone_id=zone.id, month=month,
                                      budget_litres=budget))
            db.session.commit()
        flash(f"Zone '{name}' created.", "success")
        return redirect(url_for("zones.list_zones"))
    return render_template("zone_form.html", zone=None, action="Add")


@zone_bp.route("/<int:zone_id>/edit", methods=["GET", "POST"])
def edit_zone(zone_id):
    zone = Zone.query.get_or_404(zone_id)
    if request.method == "POST":
        zone.name               = request.form.get("name", zone.name).strip()
        zone.baseline_flow_rate = request.form.get("baseline_flow_rate", zone.baseline_flow_rate, type=float)
        zone.expected_daily_usage=request.form.get("expected_daily_usage", zone.expected_daily_usage, type=float)
        zone.location_tag       = request.form.get("location_tag", zone.location_tag).strip()
        db.session.commit()
        flash(f"Zone '{zone.name}' updated.", "success")
        return redirect(url_for("zones.list_zones"))
    return render_template("zone_form.html", zone=zone, action="Edit")


@zone_bp.route("/<int:zone_id>/delete", methods=["POST"])
def delete_zone(zone_id):
    zone = Zone.query.get_or_404(zone_id)
    name = zone.name
    db.session.delete(zone)
    db.session.commit()
    flash(f"Zone '{name}' deleted.", "info")
    return redirect(url_for("zones.list_zones"))


@zone_bp.route("/<int:zone_id>/toggle", methods=["POST"])
def toggle_zone(zone_id):
    zone = Zone.query.get_or_404(zone_id)
    zone.is_active = not zone.is_active
    db.session.commit()
    flash(f"Zone '{zone.name}' {'activated' if zone.is_active else 'deactivated'}.", "info")
    return redirect(url_for("zones.list_zones"))


@zone_bp.route("/<int:zone_id>/notes", methods=["POST"])
def add_note(zone_id):
    Zone.query.get_or_404(zone_id)
    content = request.form.get("content", "").strip()
    author  = request.form.get("author", "Operator").strip()
    if content:
        db.session.add(ZoneNote(zone_id=zone_id, content=content, author=author))
        db.session.commit()
    return redirect(url_for("zones.list_zones"))