from flask import Flask

from config import Config
from models import Zone, db
from routes.dashboard_routes import dashboard_bp
from routes.zone_routes import zone_bp
from simulator import WaterSimulator


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(zone_bp)

    with app.app_context():
        db.create_all()
        seed_data()

    simulator = WaterSimulator(app)
    simulator.start()
    app.extensions["water_simulator"] = simulator
    return app


def seed_data() -> None:
    if Zone.query.count() > 0:
        return
    zones = [
        Zone(name="Central District", expected_daily_usage=32000, baseline_flow_rate=24),
        Zone(name="North Residential", expected_daily_usage=21000, baseline_flow_rate=16),
        Zone(name="Industrial Belt", expected_daily_usage=48000, baseline_flow_rate=33),
        Zone(name="University Ward", expected_daily_usage=18000, baseline_flow_rate=14),
    ]
    db.session.add_all(zones)
    db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
