"""
WaterWise ML v2 – Machine Learning Module
Isolation Forest + Linear Regression + Health Score computation
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class WaterMLModel:
    def __init__(self, contamination=0.08, n_estimators=100):
        self.contamination  = contamination
        self.n_estimators   = n_estimators
        self._iso_forest    = None
        self._scaler        = StandardScaler()
        self._is_trained    = False
        self._reg_model     = LinearRegression()
        self._reg_trained   = False
        self._r2_score      = 0.0

    @staticmethod
    def _build_features(df):
        df = df.copy()
        df["hour"]             = df["timestamp"].dt.hour
        df["day_of_week"]      = df["timestamp"].dt.dayofweek
        df["hour_sin"]         = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"]         = np.cos(2 * np.pi * df["hour"] / 24)
        df["flow_rolling_mean"]= df["flow_rate"].rolling(3, min_periods=1).mean()
        df["flow_rolling_std"] = df["flow_rate"].rolling(3, min_periods=1).std().fillna(0)
        df["flow_diff"]        = df["flow_rate"].diff().fillna(0)
        return df[["flow_rate","pressure","hour_sin","hour_cos",
                   "day_of_week","flow_rolling_mean","flow_rolling_std","flow_diff"]].values

    def train_anomaly(self, df):
        try:
            if len(df) < 10: return False
            X = self._scaler.fit_transform(self._build_features(df))
            self._iso_forest = IsolationForest(
                n_estimators=self.n_estimators,
                contamination=self.contamination,
                random_state=42, n_jobs=-1)
            self._iso_forest.fit(X)
            self._is_trained = True
            return True
        except Exception as e:
            logger.error("Anomaly training failed: %s", e)
            return False

    def predict_anomaly(self, df):
        df = df.copy()
        if not self._is_trained:
            df["anomaly_score"] = 0.0
            df["is_anomaly"]    = False
            df["label"]         = "Normal"
            return df
        try:
            X     = self._scaler.transform(self._build_features(df))
            raw   = self._iso_forest.decision_function(X)
            preds = self._iso_forest.predict(X)
            mn, mx = raw.min(), raw.max()
            norm  = 1 - (raw - mn) / (mx - mn) if mx != mn else np.zeros_like(raw)
            df["anomaly_score"] = norm
            df["is_anomaly"]    = preds == -1
            df["label"]         = df.apply(
                lambda r: self._label(r["is_anomaly"], r["anomaly_score"], r["flow_rate"]), axis=1)
        except Exception as e:
            logger.warning("Anomaly prediction failed: %s", e)
            df["anomaly_score"] = 0.0
            df["is_anomaly"]    = False
            df["label"]         = "Normal"
        return df

    @staticmethod
    def _label(is_anom, score, flow):
        if not is_anom: return "Normal"
        return "Leak Risk" if score > 0.75 or flow > 5.0 else "Anomaly"

    def train_prediction(self, df):
        try:
            if len(df) < 20: return 0.0
            df = df.copy()
            df["hour_sin"] = np.sin(2 * np.pi * df["timestamp"].dt.hour / 24)
            df["hour_cos"] = np.cos(2 * np.pi * df["timestamp"].dt.hour / 24)
            df["dow"]      = df["timestamp"].dt.dayofweek
            X, y = df[["hour_sin","hour_cos","dow"]].values, df["total_volume"].values
            from sklearn.model_selection import train_test_split
            Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
            self._reg_model.fit(Xtr, ytr)
            self._r2_score  = max(0.0, self._reg_model.score(Xte, yte))
            self._reg_trained = True
            return self._r2_score
        except Exception as e:
            logger.error("Prediction training failed: %s", e)
            return 0.0

    def predict_usage(self):
        if not self._reg_trained:
            return {"predicted_hour_usage": 0.0, "predicted_day_usage": 0.0, "confidence": 0.0}
        try:
            now   = datetime.utcnow()
            preds = []
            for i in range(1, 25):
                h    = (now + timedelta(hours=i)).hour
                pred = self._reg_model.predict([[
                    np.sin(2*np.pi*h/24), np.cos(2*np.pi*h/24), now.weekday()
                ]])[0]
                preds.append(max(0.0, pred))
            return {
                "predicted_hour_usage": round(float(preds[0]), 2),
                "predicted_day_usage":  round(float(sum(preds)), 2),
                "confidence": round(self._r2_score, 4),
            }
        except:
            return {"predicted_hour_usage": 0.0, "predicted_day_usage": 0.0, "confidence": 0.0}

    def compute_health_score(self, recent_readings):
        """
        Composite health score 0-100:
          60pts  flow normalcy
          25pts  anomaly rate
          15pts  pressure stability
        """
        if not recent_readings:
            return 100.0, "A"
        flows     = [r.flow_rate     for r in recent_readings]
        pressures = [r.pressure      for r in recent_readings]
        anom_rate = sum(1 for r in recent_readings if r.is_anomaly) / len(recent_readings)

        # Flow score
        baselines = [r.flow_rate for r in recent_readings]
        mean_flow = np.mean(flows)
        flow_score = max(0, 60 - 60 * min(1, abs(mean_flow - np.median(flows)) / (np.median(flows) + 1e-6)))

        # Anomaly score
        anom_score = 25 * (1 - anom_rate)

        # Pressure stability
        press_cv   = np.std(pressures) / (np.mean(pressures) + 1e-6)
        press_score= max(0, 15 * (1 - min(1, press_cv * 5)))

        total = flow_score + anom_score + press_score
        grade = "A" if total >= 85 else "B" if total >= 70 else "C" if total >= 55 else "D" if total >= 40 else "F"
        return round(total, 1), grade


# ── Global registry ───────────────────────────────────────────────────────────
_models: dict = {}

def get_model(zone_id, contamination=0.08):
    if zone_id not in _models:
        _models[zone_id] = WaterMLModel(contamination=contamination)
    return _models[zone_id]

def train_all_models(app, min_rows=30):
    with app.app_context():
        from models import Zone, WaterReading
        import pandas as pd
        for zone in Zone.query.filter_by(is_active=True).all():
            rows = (WaterReading.query.filter_by(zone_id=zone.id)
                    .order_by(WaterReading.timestamp.asc()).all())
            if len(rows) < min_rows: continue
            df = pd.DataFrame([{
                "timestamp": r.timestamp, "flow_rate": r.flow_rate,
                "total_volume": r.total_volume, "pressure": r.pressure,
            } for r in rows])
            m = get_model(zone.id)
            m.train_anomaly(df)
            m.train_prediction(df)
        logger.info("All models retrained.")