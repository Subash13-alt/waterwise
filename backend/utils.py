"""
WaterWise ML v2 – Utilities
New: heatmap data, budget progress, health trend
"""
import csv, io, random, math, logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SEED_ZONES = [
    {"name": "Residential North",  "baseline_flow_rate": 1.2, "expected_daily_usage": 4500,  "location_tag": "North Block"},
    {"name": "Commercial East",    "baseline_flow_rate": 2.5, "expected_daily_usage": 9000,  "location_tag": "East Market"},
    {"name": "Industrial West",    "baseline_flow_rate": 4.0, "expected_daily_usage": 14000, "location_tag": "West Industrial"},
    {"name": "Residential South",  "baseline_flow_rate": 1.0, "expected_daily_usage": 3800,  "location_tag": "South Block"},
    {"name": "Park & Recreation",  "baseline_flow_rate": 0.8, "expected_daily_usage": 2000,  "location_tag": "Central Park"},
]


def seed_database(app):
    with app.app_context():
        from extensions import db
        from models import Zone, WaterReading, ZoneBudget, ZoneNote
        db.create_all()
        if Zone.query.count() > 0:
            logger.info("Already seeded – skip.")
            return
        logger.info("Seeding …")

        zones = []
        for z in SEED_ZONES:
            zone = Zone(**z)
            db.session.add(zone)
            zones.append(zone)
        db.session.commit()

        # Historical readings (48 h)
        now = datetime.utcnow()
        readings = []
        for zone in zones:
            bl = zone.baseline_flow_rate
            for m in range(48*60, 0, -1):
                ts   = now - timedelta(minutes=m)
                diur = 1.0 + 0.4 * math.sin(math.pi * (ts.hour - 6) / 12)
                noise= random.gauss(0, 0.05 * bl)
                flow = max(0.01, bl * diur + noise)
                if random.random() < 0.03:
                    flow = bl * random.uniform(1.9, 3.0)
                readings.append(WaterReading(
                    zone_id=zone.id, timestamp=ts,
                    flow_rate=round(flow, 4), total_volume=round(flow*5, 4),
                    pressure=round(max(0.5, random.gauss(3.5, 0.3)), 3),
                    label="Normal"))
        db.session.bulk_save_objects(readings)

        # Budgets for this month
        month = now.strftime("%Y-%m")
        for zone in zones:
            db.session.add(ZoneBudget(
                zone_id=zone.id, month=month,
                budget_litres=zone.expected_daily_usage * 30,
                alert_threshold=0.85))

        # Seed notes
        sample_notes = [
            "Pipe inspection scheduled next week.",
            "Pressure regulator replaced last month.",
            "High usage during peak hours – monitor.",
        ]
        for i, zone in enumerate(zones):
            db.session.add(ZoneNote(
                zone_id=zone.id,
                content=sample_notes[i % len(sample_notes)],
                author="System", pinned=(i == 0)))

        db.session.commit()
        logger.info("Seeded %d zones, %d readings.", len(zones), len(readings))

        from ml_model import train_all_models
        train_all_models(app)


# ── Heatmap Data ──────────────────────────────────────────────────────────────
def anomaly_heatmap(zone_id=None):
    """
    Returns a 7×24 matrix: rows=days(Mon–Sun), cols=hours(0–23).
    Cell value = anomaly count in that slot over last 30 days.
    """
    from models import WaterReading
    cutoff = datetime.utcnow() - timedelta(days=30)
    q = WaterReading.query.filter(
        WaterReading.timestamp >= cutoff, WaterReading.is_anomaly == True)
    if zone_id:
        q = q.filter(WaterReading.zone_id == zone_id)
    rows = q.all()

    matrix = [[0]*24 for _ in range(7)]
    for r in rows:
        dow  = r.timestamp.weekday()   # 0=Mon
        hour = r.timestamp.hour
        matrix[dow][hour] += 1
    return matrix


# ── Budget Progress ───────────────────────────────────────────────────────────
def budget_progress(zone_id=None):
    from models import Zone, ZoneBudget, WaterReading
    from extensions import db
    from sqlalchemy import func
    month = datetime.utcnow().strftime("%Y-%m")
    start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)

    zones = Zone.query.filter_by(is_active=True).all()
    if zone_id:
        zones = [z for z in zones if z.id == zone_id]

    result = []
    for zone in zones:
        budget = ZoneBudget.query.filter_by(zone_id=zone.id, month=month).first()
        if not budget: continue
        used = db.session.query(func.sum(WaterReading.total_volume)).filter(
            WaterReading.zone_id == zone.id, WaterReading.timestamp >= start).scalar() or 0
        pct  = min(100, round(used / budget.budget_litres * 100, 1))
        result.append({
            "zone_id": zone.id, "zone_name": zone.name,
            "budget_l": budget.budget_litres, "used_l": round(float(used), 2),
            "pct": pct, "month": month,
            "status": "danger" if pct >= 100 else "warning" if pct >= budget.alert_threshold*100 else "safe",
        })
    return result


# ── Top Loss ──────────────────────────────────────────────────────────────────
def get_top_loss_zones(limit=3):
    from models import Zone, WaterReading
    from config import Config
    cutoff = datetime.utcnow() - timedelta(hours=24)
    results = []
    for zone in Zone.query.filter_by(is_active=True).all():
        bl = zone.baseline_flow_rate
        rows = WaterReading.query.filter(
            WaterReading.zone_id == zone.id, WaterReading.timestamp >= cutoff).all()
        if not rows: continue
        excess = sum(max(0, r.flow_rate - bl) * 5 for r in rows if r.is_anomaly)
        anom   = sum(1 for r in rows if r.is_anomaly)
        total  = len(rows)
        results.append({
            "zone": zone, "excess_volume": round(excess, 2),
            "anomaly_count": anom,
            "anomaly_pct": round(anom/total*100, 1) if total else 0,
            "financial_loss": round((excess/1000)*Config.COST_PER_1000_LITERS, 2),
        })
    results.sort(key=lambda x: x["excess_volume"], reverse=True)
    return results[:limit]


# ── Monthly Summary ───────────────────────────────────────────────────────────
def monthly_summary():
    from models import WaterReading
    from extensions import db
    from sqlalchemy import func
    cutoff = datetime.utcnow() - timedelta(days=30)
    rows = (db.session.query(
        func.date(WaterReading.timestamp).label("day"),
        func.sum(WaterReading.total_volume).label("vol"),
        func.count(WaterReading.id).label("cnt"),
        func.sum(db.case((WaterReading.is_anomaly==True, 1), else_=0)).label("anom"))
        .filter(WaterReading.timestamp >= cutoff)
        .group_by(func.date(WaterReading.timestamp))
        .order_by(func.date(WaterReading.timestamp).desc())
        .limit(30).all())
    return [{"day": str(r.day), "total_vol": round(float(r.vol or 0), 2),
             "reading_count": r.cnt, "anomaly_count": r.anom} for r in rows]


# ── CSV Export ────────────────────────────────────────────────────────────────
def export_readings_csv(zone_id=None, limit=5000):
    from models import WaterReading
    q = WaterReading.query.order_by(WaterReading.timestamp.desc()).limit(limit)
    if zone_id:
        q = WaterReading.query.filter_by(zone_id=zone_id).order_by(
            WaterReading.timestamp.desc()).limit(limit)
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["id","zone_id","timestamp","flow_rate","total_volume",
                "pressure","is_anomaly","anomaly_score","label"])
    for r in q.all():
        w.writerow([r.id, r.zone_id, r.timestamp, r.flow_rate, r.total_volume,
                    r.pressure, r.is_anomaly, r.anomaly_score, r.label])
    return output.getvalue()