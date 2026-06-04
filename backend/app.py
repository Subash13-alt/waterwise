"""
WaterWise ML v2 - Application Factory
Static files served from backend/static/ (Flask default location)
"""
import sys
import os

_BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BACKEND)

import logging
from flask import Flask, render_template
from config import Config
from extensions import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app():
    # Flask looks for static/ and templates/ inside _BACKEND by default
    app = Flask(
        __name__,
        static_folder=os.path.join(_BACKEND, "static"),
        static_url_path="/static",
        template_folder=os.path.join(_BACKEND, "templates"),
    )

    print(f"\n[PATH] static    -> {app.static_folder}")
    print(f"[PATH] templates -> {app.template_folder}")
    print(f"[PATH] static exists    = {os.path.exists(app.static_folder)}")
    print(f"[PATH] templates exists = {os.path.exists(app.template_folder)}\n")

    app.config.from_object(Config)
    db.init_app(app)

    # Blueprints
    from routes.dashboard_routes import dashboard_bp
    from routes.zone_routes      import zone_bp
    from routes.api_routes       import api_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(zone_bp)
    app.register_blueprint(api_bp)

    # Page routes
    @app.route("/analytics")
    def analytics():
        return render_template("analytics.html")

    @app.route("/alerts")
    def alert_history_page():
        from models import Zone
        zones = Zone.query.filter_by(is_active=True).all()
        return render_template("alert_history.html", zones=zones)

    @app.route("/heatmap")
    def heatmap_page():
        from models import Zone
        zones = Zone.query.filter_by(is_active=True).all()
        return render_template("heatmap.html", zones=zones)

    @app.route("/budget")
    def budget_page():
        from models import Zone
        zones = Zone.query.filter_by(is_active=True).all()
        return render_template("budget.html", zones=zones)

    # Seed DB and start simulator
    with app.app_context():
        from utils import seed_database
        seed_database(app)

    from simulator import start_simulator
    start_simulator(app, interval=Config.SIMULATION_INTERVAL_SECONDS)

    return app