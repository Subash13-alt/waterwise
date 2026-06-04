"""
WaterWise ML v2 – Simulator with Health Score tracking
"""
import random, math, threading, time, logging
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)
_forced_leaks: set = set()
_sim_running = False
_sim_thread  = None


def simulate_leak(zone_id):
    _forced_leaks.add(zone_id)
    logger.info("Leak injected zone=%d", zone_id)
    def _clear():
        time.sleep(30)
        _forced_leaks.discard(zone_id)
    threading.Thread(target=_clear, daemon=True).start()


def _flow(baseline, hour, forced=False):
    if forced:
        return baseline * random.uniform(2.0, 4.0)
    if random.random() < 0.04:
        return baseline * random.uniform(1.9, 3.0)
    diurnal = 1.0 + 0.4 * math.sin(math.pi * (hour - 6) / 12)
    return max(0.01, baseline * diurnal + random.gauss(0, 0.05 * baseline))


def _run(app, interval):
    global _sim_running
    with app.app_context():
        from models import Zone, WaterReading, HealthScore
        from extensions import db
        from alert_engine import evaluate_reading
        from ml_model import get_model, train_all_models
        import pandas as pd

        train_all_models(app)
        tick = 0

        while _sim_running:
            try:
                zones = Zone.query.filter_by(is_active=True).all()
                for zone in zones:
                    now   = datetime.utcnow()
                    hour  = now.hour
                    forced = zone.id in _forced_leaks
                    fr    = _flow(zone.baseline_flow_rate, hour, forced)
                    vol   = fr * interval
                    pres  = max(0.5, random.gauss(3.5, 0.3))

                    r = WaterReading(
                        zone_id=zone.id, timestamp=now,
                        flow_rate=round(fr, 4), total_volume=round(vol, 4),
                        pressure=round(pres, 3), label="Normal")
                    db.session.add(r)
                    db.session.flush()

                    # ML scoring
                    model = get_model(zone.id)
                    if model._is_trained:
                        df = pd.DataFrame([{"timestamp": r.timestamp,
                            "flow_rate": r.flow_rate, "total_volume": r.total_volume,
                            "pressure": r.pressure}])
                        scored = model.predict_anomaly(df)
                        r.anomaly_score = float(scored["anomaly_score"].iloc[0])
                        r.is_anomaly    = bool(scored["is_anomaly"].iloc[0])
                        r.label         = scored["label"].iloc[0]

                    db.session.commit()
                    evaluate_reading(r, zone)

                    # Health score every 12 ticks (~1 min)
                    if tick % 12 == 0:
                        recent = (WaterReading.query.filter_by(zone_id=zone.id)
                                  .order_by(WaterReading.timestamp.desc()).limit(20).all())
                        score, grade = model.compute_health_score(recent)
                        db.session.add(HealthScore(zone_id=zone.id, score=score, grade=grade))
                        db.session.commit()

                tick += 1
                if tick % 60 == 0:
                    train_all_models(app)
                if tick % 120 == 0:
                    _prune(app)

            except Exception as e:
                logger.error("Sim tick error: %s", e)
                try: db.session.rollback()
                except: pass
            time.sleep(interval)


def _prune(app):
    with app.app_context():
        from models import Zone, WaterReading, HealthScore
        from extensions import db
        for zone in Zone.query.all():
            cnt = WaterReading.query.filter_by(zone_id=zone.id).count()
            if cnt > 2000:
                oldest = (WaterReading.query.filter_by(zone_id=zone.id)
                          .order_by(WaterReading.timestamp.asc()).limit(cnt-2000).all())
                for r in oldest: db.session.delete(r)
            hcnt = HealthScore.query.filter_by(zone_id=zone.id).count()
            if hcnt > 500:
                hold = (HealthScore.query.filter_by(zone_id=zone.id)
                        .order_by(HealthScore.timestamp.asc()).limit(hcnt-500).all())
                for h in hold: db.session.delete(h)
        db.session.commit()


def start_simulator(app, interval=5):
    global _sim_running, _sim_thread
    if _sim_running: return
    _sim_running = True
    _sim_thread  = threading.Thread(target=_run, args=(app, interval), daemon=True)
    _sim_thread.start()
    logger.info("Simulator started (interval=%ds)", interval)