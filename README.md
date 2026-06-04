# 💧 WaterWise ML v2 – Smart Water Leak Detection System

A production-ready full-stack Python web application with ML anomaly detection,
real-time simulation, budget planning, anomaly heatmaps, and health scoring.

---

## 📁 Project Structure

```
waterwise_v2/
│
├── run.py                          ← START HERE — single entry point
├── .gitignore
├── README.md
│
├── backend/                        ← All Python / Flask code
│   ├── app.py                      ← Flask app factory
│   ├── config.py                   ← All settings & thresholds
│   ├── extensions.py               ← SQLAlchemy instance
│   ├── models.py                   ← ORM: Zone, Reading, Alert, Budget, Note, Health
│   ├── ml_model.py                 ← Isolation Forest + Linear Regression
│   ├── simulator.py                ← Background data generator (every 5s)
│   ├── alert_engine.py             ← Rule-based + ML + budget alerts
│   ├── utils.py                    ← Seed data, heatmap, CSV export
│   ├── requirements.txt
│   ├── data/
│   │   └── waterwise.db            ← SQLite DB (auto-created on first run)
│   └── routes/
│       ├── __init__.py
│       ├── dashboard_routes.py
│       ├── zone_routes.py
│       └── api_routes.py
│
└── frontend/                       ← All HTML / CSS / JS
    ├── templates/
    │   ├── base.html               ← Master layout (sidebar, topbar, SSE)
    │   ├── dashboard.html          ← Live dashboard + 4 charts
    │   ├── heatmap.html            ← Anomaly heatmap (7×24 grid)
    │   ├── budget.html             ← Monthly budget planner
    │   ├── alert_history.html      ← Paginated alert log + filters
    │   ├── analytics.html          ← Top loss, predictions, health, monthly
    │   ├── zones.html              ← Zone list + operator notes
    │   └── zone_form.html          ← Add / Edit zone form
    └── static/
        ├── css/styles.css          ← Complete design system (glassmorphism)
        └── js/
            ├── app.js              ← Theme, sidebar, clock, toasts, SSE
            └── dashboard.js        ← All Chart.js logic + live refresh
```

---

## 🚀 How to Run

### Step 1 – Open a terminal in the project root

```
waterwise_v2\          ← you must be here (where run.py is)
```

### Step 2 – Create virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3 – Install dependencies

```bash
pip install -r backend/requirements.txt
```

### Step 4 – Run the app

```bash
python run.py
```

### Step 5 – Open in browser

| Page            | URL                              |
|-----------------|----------------------------------|
| Dashboard       | http://localhost:5000            |
| Anomaly Heatmap | http://localhost:5000/heatmap    |
| Budget Planner  | http://localhost:5000/budget     |
| Alert History   | http://localhost:5000/alerts     |
| Analytics       | http://localhost:5000/analytics  |
| Zone Manager    | http://localhost:5000/zones/     |

> The app auto-seeds 5 zones with 48 h of history and trains ML models on first run.

---

## ✨ Features

### Core
| Feature | Detail |
|---------|--------|
| Live simulation | New readings every 5 seconds per zone |
| Isolation Forest | Anomaly detection with Normal / Anomaly / Leak Risk labels |
| Linear Regression | Next-hour & next-day usage prediction |
| Rule engine | High flow · Consecutive leak · Night usage detection |
| SSE push | Critical alerts pushed via Server-Sent Events (no polling needed) |

### New in v2
| Feature | Detail |
|---------|--------|
| 🗺 Anomaly Heatmap | 7-day × 24-hour anomaly density grid |
| 💰 Budget Planner | Monthly water budget per zone with progress bars |
| ❤️ Health Score | Composite 0–100 score + A–F grade per zone |
| 📋 Alert History | Paginated, filterable full alert log |
| 📝 Operator Notes | Add/delete notes per zone |
| 💸 Budget Alerts | Auto-alert when zone hits 85% of monthly budget |

### Alerts Generated
| Type | Severity | Trigger |
|------|----------|---------|
| High Flow | High | Flow > 1.8× baseline |
| Leak Detected | Critical | 3 consecutive high-flow readings |
| Night Usage | Medium | Any flow > 0.3 L/s between 22:00–06:00 |
| ML Anomaly | Medium | Isolation Forest flags reading |
| High Risk | Critical | ML score > 0.75 or flow > 5 L/s |
| Budget Alert | High | Zone reaches 85% of monthly budget |

### Demo Mode
Click **"Inject Leak"** on any zone tile to simulate a burst pipe for 30 seconds.
Both ML and rule-based alerts fire within two refresh cycles.

---

## 🔧 Configuration (`backend/config.py`)

```python
HIGH_FLOW_MULTIPLIER          = 1.8    # threshold multiplier
CONSECUTIVE_ABNORMAL_FOR_LEAK = 3      # readings before Leak Detected
NIGHT_HOURS                   = (22,6) # night detection window
ISOLATION_FOREST_CONTAMINATION= 0.08  # expected anomaly fraction
COST_PER_1000_LITERS          = 20    # ₹ per 1000 L (financial calc)
SIMULATION_INTERVAL_SECONDS   = 5     # how often simulator fires
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | KPI aggregates |
| GET | `/api/flow/all` | Latest reading per zone |
| GET | `/api/flow/<zone_id>` | Last N readings |
| GET | `/api/alerts` | Active alerts |
| GET | `/api/alerts/history` | Full paginated alert log |
| POST | `/api/alerts/<id>/resolve` | Resolve alert |
| GET | `/api/consumption/zones` | 24h consumption per zone |
| GET | `/api/prediction/all` | ML usage predictions |
| GET | `/api/heatmap` | 7×24 anomaly density matrix |
| GET | `/api/budget` | Monthly budget progress |
| POST | `/api/budget/set` | Set zone budget |
| GET | `/api/health` | Zone health scores + trend |
| GET | `/api/notes/<zone_id>` | Zone operator notes |
| POST | `/api/notes` | Add note |
| DELETE | `/api/notes/<id>` | Delete note |
| POST | `/api/demo/inject_leak/<id>` | Inject test anomaly |
| GET | `/api/sse/live` | Server-Sent Events stream |
| GET | `/api/export/csv` | Download readings as CSV |
| GET | `/api/analytics/top_loss` | Top water-loss zones |
| GET | `/api/analytics/monthly` | 30-day daily summary |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask 3.0 |
| Database | SQLite + SQLAlchemy ORM |
| Frontend | HTML5, Bootstrap 5, Jinja2 |
| Charts | Chart.js 4 |
| ML | scikit-learn (IsolationForest, LinearRegression) |
| Data | pandas, numpy |
| Real-time | Server-Sent Events (SSE) |