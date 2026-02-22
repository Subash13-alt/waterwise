# WaterWise – Smart Water Leak & Usage Monitoring System

WaterWise is a production-style Flask application for real-time, **rule-based** water monitoring across city zones.

> No AI/ML/NLP used. Detection is purely threshold and rules driven.

## Features

- Zone CRUD (add/edit/delete)
- Background flow simulation every 5 seconds
- Rule-based alert engine:
  - High Risk: `current_flow > baseline_flow * 1.8`
  - Leak Detected: 3 consecutive high-risk readings
  - Suspicious Usage: high flow between 12 AM and 4 AM
- Dashboard KPIs + charts (Chart.js)
- Alert center in UI + email notification (SMTP or console mock)
- Government analytics panel:
  - Top 3 high-loss zones
  - Estimated water loss and financial impact
  - Monthly summary + CSV export
- Basic admin login system
- Demo mode leak trigger via `simulate_leak(zone_id)`

## Architecture

```text
waterwise/
├── app.py
├── config.py
├── models.py
├── simulator.py
├── alert_engine.py
├── routes/
│   ├── __init__.py
│   ├── zone_routes.py
│   └── dashboard_routes.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── zones.html
│   └── analytics.html
├── static/
│   └── css/style.css
├── data/sample_readings.csv
├── requirements.txt
└── README.md
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://localhost:5000`

Default login:
- Username: `admin`
- Password: `admin123`

## Configuration

Set environment variables if needed:

- `SECRET_KEY`
- `DATABASE_URL` (default sqlite)
- `SIMULATION_INTERVAL_SECONDS`
- `SMTP_ENABLED=true|false`
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- `ALERT_FROM_EMAIL`, `ALERT_TO_EMAIL`
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`

## Hackathon Demo Script

1. Login and open **Zones** page.
2. Click **Simulate Leak** for one zone.
3. Wait 10–20 seconds (simulation ticks every 5 sec).
4. Go to dashboard and observe:
   - Alerts count increase
   - Critical leak alert in recent alerts
   - Zone highlighted red
5. Open **Analytics** page to view top high-loss zones.
6. Export monthly report CSV.

## Rule Engine Notes (No AI)

- Uses deterministic thresholds from config and zone baselines.
- Tracks consecutive abnormal readings from persisted DB rows.
- Night-time suspicious pattern uses fixed hour window.

## Future Scalability Ideas

- Replace SQLite with PostgreSQL and Timescale hypertables.
- Use Celery/RQ for distributed simulation and alert workers.
- Add Redis caching and WebSocket push for live dashboards.
- Add multi-tenant departments and role-based access control.
- Add IoT ingestion endpoint for real sensor meters.

## API Endpoints (high level)

- `GET /` Dashboard
- `GET /api/flow-trends`
- `GET /analytics`
- `GET /analytics/export`
- `GET|POST /login`, `GET /logout`
- `GET /zones/`, `POST /zones/add`, `POST /zones/<id>/edit`, `POST /zones/<id>/delete`
- `POST /simulate-leak/<zone_id>`

