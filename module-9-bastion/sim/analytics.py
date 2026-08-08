"""
Supply concentration analytics for Bastion.

HHI (Herfindahl-Hirschman Index) is computed on a 0-10,000 scale from
country production shares (as fractions summing to ~1.0).

HHI < 1,500   -> Competitive / low concentration
1,500-2,500   -> Moderate concentration
> 2,500        -> High concentration (single-source risk)
"""

SUBSTITUTABILITY_WEIGHT = {
    "Very Low": 1.0,
    "Low": 0.75,
    "Moderate": 0.5,
    "High": 0.25,
}


def compute_hhi(producing_countries: dict) -> float:
    """Herfindahl-Hirschman Index from a dict of {country: share}."""
    return sum((share * 100) ** 2 for share in producing_countries.values())


def hhi_band(hhi: float) -> str:
    if hhi > 2500:
        return "High concentration"
    if hhi > 1500:
        return "Moderate concentration"
    return "Competitive"


def concentration_risk_score(mineral: dict) -> float:
    """
    Composite 0-100 risk score blending supply concentration (HHI) and
    substitutability. Higher = more supply chain risk.
    """
    hhi = compute_hhi(mineral["producing_countries"])
    hhi_component = min(hhi / 10000, 1.0) * 70  # HHI max is 10,000
    sub_component = SUBSTITUTABILITY_WEIGHT.get(mineral["substitutability"], 0.5) * 30
    return round(hhi_component + sub_component, 1)


def dominant_supplier(mineral: dict):
    country, share = max(mineral["producing_countries"].items(), key=lambda kv: kv[1])
    return country, share