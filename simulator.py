from __future__ import annotations

import random
import threading
import time
from datetime import datetime

from flask import Flask

from alert_engine import AlertEngine
from models import FlowReading, Zone, db


class WaterSimulator:
    def __init__(self, app: Flask):
        self.app = app
        self._thread = None
        self._stop_event = threading.Event()
        self._leak_zone_flags: dict[int, int] = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def simulate_leak(self, zone_id: int) -> None:
        # force next 4 readings to be high and trigger leak rule
        self._leak_zone_flags[zone_id] = 4

    def _run_loop(self) -> None:
        with self.app.app_context():
            while not self._stop_event.is_set():
                self._tick()
                time.sleep(self.app.config["SIMULATION_INTERVAL_SECONDS"])

    def _tick(self) -> None:
        zones = Zone.query.all()
        for zone in zones:
            flow_rate = self._generate_flow(zone)
            volume = flow_rate * self.app.config["SIMULATION_INTERVAL_SECONDS"] / 60.0
            reading = FlowReading(
                zone_id=zone.id,
                timestamp=datetime.utcnow(),
                flow_rate=flow_rate,
                total_volume=volume,
                simulated_leak=self._leak_zone_flags.get(zone.id, 0) > 0,
            )
            db.session.add(reading)
            db.session.commit()
            AlertEngine.evaluate_reading(reading)

    def _generate_flow(self, zone: Zone) -> float:
        forced = self._leak_zone_flags.get(zone.id, 0)
        if forced > 0:
            self._leak_zone_flags[zone.id] = forced - 1
            return round(zone.baseline_flow_rate * random.uniform(2.0, 2.6), 2)

        baseline = zone.baseline_flow_rate
        return round(max(0.1, random.gauss(mu=baseline, sigma=baseline * 0.18)), 2)
