"""
Discrete-event simulation of a critical mineral supply disruption using
SimPy. A disruption event is injected at t=0 (day 0). Availability for
the affected mineral drops immediately by `severity`, then recovers
stochastically (triangular distribution) over the horizon. Application
sectors downstream of the mineral inherit the availability shortfall,
weighted by how dependent each sector is assumed to be.

This is a systems/analytics demonstration, not a calibrated economic
forecasting model. Recovery-time ranges are loosely informed by
historical analogues (e.g. 2010 China REE export quota episode,
2023 Ge/Ga export control response window) but are illustrative.
"""

import random
import simpy


# Loose historical-analogue recovery windows (days), by severity tier.
RECOVERY_WINDOWS = {
    "Low": (30, 60, 90),        # (min, mode, max) for triangular dist
    "Moderate": (90, 180, 270),
    "Severe": (180, 365, 540),
}


def _sector_dependency_weight(application: str) -> float:
    """
    Rough relative dependency weight per application sector — how hard
    that sector is hit, proportionally, by a supply shortfall. Not
    empirically derived; illustrative only.
    """
    weights = {
        "Aerospace": 0.9,
        "Magnetics": 0.9,
        "Medical (MRI magnets)": 0.85,
        "Medical (implants)": 0.6,
        "Medical (infrared optics)": 0.6,
        "Medical (dental alloys)": 0.5,
        "Computer Hardware": 0.8,
        "Computer Hardware (semiconductors)": 0.85,
        "Computer Hardware (RF)": 0.8,
        "Lasers": 0.7,
        "Catalysts": 0.6,
        "Metal Alloys": 0.65,
        "Batteries": 0.85,
        "Aerospace (superalloys)": 0.9,
        "Aerospace (alloys)": 0.85,
        "Aerospace (flame retardants)": 0.55,
    }
    return weights.get(application, 0.6)


class DisruptionSimulation:
    """
    Wraps a SimPy environment to model one disruption event and its
    cascading availability impact across the mineral's application
    sectors over `horizon_days`.
    """

    def __init__(self, mineral: dict, source_country: str, severity: str,
                 horizon_days: int = 540, seed: int | None = None):
        self.mineral = mineral
        self.source_country = source_country
        self.severity = severity
        self.horizon_days = horizon_days
        self.rng = random.Random(seed)

        self.env = simpy.Environment()
        self.timeline = []  # list of dicts: day, availability_pct

        share_lost = mineral["producing_countries"].get(source_country, 0.0)
        severity_multiplier = {"Low": 0.4, "Moderate": 0.7, "Severe": 1.0}[severity]
        self.initial_drop_pct = min(share_lost * severity_multiplier * 100, 95.0)

        lo, mode, hi = RECOVERY_WINDOWS[severity]
        self.recovery_days = self.rng.triangular(lo, hi, mode)

    def _availability_curve(self, day: int) -> float:
        """Availability as % of normal supply at a given day."""
        if day <= 0:
            return 100.0
        if day >= self.recovery_days:
            return 100.0
        # Linear recovery from (100 - drop) back to 100 over recovery_days,
        # with a small stochastic jitter to avoid a perfectly straight line.
        floor = 100.0 - self.initial_drop_pct
        progress = day / self.recovery_days
        jitter = self.rng.uniform(-1.5, 1.5)
        value = floor + (100.0 - floor) * progress + jitter
        return max(0.0, min(100.0, value))

    def _recorder(self):
        step = max(1, self.horizon_days // 120)  # ~120 sample points
        for day in range(0, self.horizon_days + 1, step):
            self.timeline.append({
                "day": day,
                "mineral_availability_pct": round(self._availability_curve(day), 1),
            })
            yield self.env.timeout(step)

    def run(self):
        self.env.process(self._recorder())
        self.env.run(until=self.horizon_days)
        return self.timeline

    def sector_impact_timeline(self):
        """Per-application-sector availability, applying dependency weights."""
        if not self.timeline:
            self.run()
        results = {}
        for app in self.mineral["applications"]:
            w = _sector_dependency_weight(app)
            results[app] = [
                {
                    "day": pt["day"],
                    "sector_availability_pct": round(
                        100 - (100 - pt["mineral_availability_pct"]) * w, 1
                    ),
                }
                for pt in self.timeline
            ]
        return results

    def summary(self):
        if not self.timeline:
            self.run()
        min_point = min(self.timeline, key=lambda p: p["mineral_availability_pct"])
        return {
            "mineral": self.mineral["name"],
            "source_country": self.source_country,
            "severity": self.severity,
            "initial_drop_pct": round(self.initial_drop_pct, 1),
            "trough_availability_pct": min_point["mineral_availability_pct"],
            "trough_day": min_point["day"],
            "estimated_recovery_days": round(self.recovery_days),
        }