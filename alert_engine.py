from __future__ import annotations

import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from flask import current_app
from sqlalchemy import func

from models import AlertLog, FlowReading, Zone, db


class AlertEngine:
    """Rule-based leak detection and alert generation."""

    @staticmethod
    def evaluate_reading(reading: FlowReading) -> list[AlertLog]:
        created_alerts = []
        zone = reading.zone
        if not zone:
            return created_alerts

        high_risk_threshold = zone.baseline_flow_rate * current_app.config["HIGH_RISK_MULTIPLIER"]

        if reading.flow_rate > high_risk_threshold:
            created_alerts.append(
                AlertEngine._create_alert(
                    zone.id,
                    "HIGH_RISK",
                    "warning",
                    f"Flow {reading.flow_rate:.2f} L/min exceeded high-risk threshold {high_risk_threshold:.2f} L/min.",
                )
            )

        recent = (
            FlowReading.query.filter_by(zone_id=zone.id)
            .order_by(FlowReading.timestamp.desc())
            .limit(current_app.config["LEAK_CONSECUTIVE_THRESHOLD"])
            .all()
        )
        if len(recent) == current_app.config["LEAK_CONSECUTIVE_THRESHOLD"] and all(
            item.flow_rate > high_risk_threshold for item in recent
        ):
            created_alerts.append(
                AlertEngine._create_alert(
                    zone.id,
                    "LEAK_DETECTED",
                    "critical",
                    "Abnormal flow persisted for 3 consecutive readings. Leak detected.",
                )
            )

        hour = reading.timestamp.hour
        night_threshold = zone.baseline_flow_rate * current_app.config["NIGHT_USAGE_MULTIPLIER"]
        if 0 <= hour < 4 and reading.flow_rate > night_threshold:
            created_alerts.append(
                AlertEngine._create_alert(
                    zone.id,
                    "SUSPICIOUS_USAGE",
                    "warning",
                    f"Night usage spike: {reading.flow_rate:.2f} L/min > {night_threshold:.2f} L/min.",
                )
            )

        db.session.commit()

        for alert in created_alerts:
            if alert.alert_type == "LEAK_DETECTED":
                AlertEngine.send_email_alert(alert)
        return created_alerts

    @staticmethod
    def _create_alert(zone_id: int, alert_type: str, severity: str, message: str) -> AlertLog:
        recent_duplicate = (
            AlertLog.query.filter_by(zone_id=zone_id, alert_type=alert_type)
            .filter(AlertLog.timestamp >= datetime.utcnow() - timedelta(minutes=2))
            .first()
        )
        if recent_duplicate:
            return recent_duplicate

        alert = AlertLog(
            zone_id=zone_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
        )
        db.session.add(alert)
        return alert

    @staticmethod
    def send_email_alert(alert: AlertLog) -> None:
        zone = Zone.query.get(alert.zone_id)
        subject = f"[WaterWise] Leak Detected in {zone.name if zone else 'Unknown Zone'}"
        body = (
            f"Alert Type: {alert.alert_type}\n"
            f"Severity: {alert.severity}\n"
            f"Time: {alert.timestamp}\n"
            f"Message: {alert.message}\n"
        )

        if not current_app.config["SMTP_ENABLED"]:
            print("EMAIL ALERT (MOCK):", subject)
            print(body)
            return

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = current_app.config["ALERT_FROM_EMAIL"]
        msg["To"] = current_app.config["ALERT_TO_EMAIL"]
        msg.set_content(body)

        with smtplib.SMTP(current_app.config["SMTP_SERVER"], current_app.config["SMTP_PORT"]) as server:
            if current_app.config["SMTP_USE_TLS"]:
                server.starttls()
            if current_app.config["SMTP_USERNAME"]:
                server.login(current_app.config["SMTP_USERNAME"], current_app.config["SMTP_PASSWORD"])
            server.send_message(msg)


def compute_loss_analytics():
    today = datetime.utcnow().date()
    results = []
    zones = Zone.query.all()
    for zone in zones:
        today_usage = (
            db.session.query(func.coalesce(func.sum(FlowReading.total_volume), 0.0))
            .filter(FlowReading.zone_id == zone.id, func.date(FlowReading.timestamp) == today)
            .scalar()
        )
        loss = max(0.0, today_usage - zone.expected_daily_usage)
        results.append({"zone": zone, "usage": today_usage, "estimated_loss": loss})
    return sorted(results, key=lambda x: x["estimated_loss"], reverse=True)
