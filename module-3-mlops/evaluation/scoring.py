"""Scoring helpers for the offline Groq evaluation.

Pure functions with no network or MLflow dependency, so they can be unit tested.
"""
import re
from statistics import mean, median
from typing import Dict, List


def extract_numbers(text: str) -> List[float]:
    """Return every number found in the text (thousands separators removed)."""
    numbers = []
    for match in re.findall(r"-?\d[\d,]*\.?\d*", text or ""):
        cleaned = match.replace(",", "").rstrip(".")
        try:
            numbers.append(float(cleaned))
        except ValueError:
            continue
    return numbers


def check_answer(answer: str, check: Dict) -> bool:
    """Apply one automatic check to a model answer."""
    text = answer or ""
    kind = check["type"]
    if kind == "contains_all":
        return all(k.lower() in text.lower() for k in check["keywords"])
    if kind == "contains_any":
        return any(k.lower() in text.lower() for k in check["keywords"])
    if kind == "regex":
        flags = 0 if check.get("case_sensitive") else re.IGNORECASE
        return re.search(check["pattern"], text, flags) is not None
    if kind == "number":
        tolerance = check.get("tolerance", 0.0)
        return any(abs(n - check["value"]) <= tolerance for n in extract_numbers(text))
    raise ValueError(f"Unknown check type: {kind}")


def cost_usd(prompt_tokens: int, completion_tokens: int, price_in_per_m: float, price_out_per_m: float) -> float:
    """Cost of one request from token counts and per-million-token prices."""
    return (prompt_tokens * price_in_per_m + completion_tokens * price_out_per_m) / 1_000_000


def percentile(values: List[float], pct: float) -> float:
    """Nearest-rank percentile (small samples, so no interpolation)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, int(round(pct / 100 * len(ordered))))
    return ordered[min(rank, len(ordered)) - 1]


def summarize(rows: List[Dict]) -> Dict[str, float]:
    """Aggregate per-question rows into the metrics logged for one run.

    Each row has: passed (bool), error (bool), latency_s, prompt_tokens, completion_tokens,
    cost_usd. A failed API call counts as a wrong answer.
    """
    n = len(rows)
    ok = [r for r in rows if not r["error"]]
    latencies_ms = [r["latency_s"] * 1000 for r in ok]
    speeds = [r["completion_tokens"] / r["latency_s"] for r in ok if r["latency_s"] > 0 and r["completion_tokens"] > 0]
    total_cost = sum(r["cost_usd"] for r in ok)
    return {
        "n_questions": n,
        "accuracy": round(sum(1 for r in rows if r["passed"]) / n, 4) if n else 0.0,
        "error_count": n - len(ok),
        "latency_ms_mean": round(mean(latencies_ms), 1) if latencies_ms else 0.0,
        "latency_ms_p50": round(median(latencies_ms), 1) if latencies_ms else 0.0,
        "latency_ms_p95": round(percentile(latencies_ms, 95), 1),
        "tokens_per_sec_mean": round(mean(speeds), 1) if speeds else 0.0,
        "prompt_tokens_total": int(sum(r["prompt_tokens"] for r in ok)),
        "completion_tokens_total": int(sum(r["completion_tokens"] for r in ok)),
        "cost_usd_total": round(total_cost, 6),
        "cost_usd_per_1k_requests": round(total_cost / len(ok) * 1000, 4) if ok else 0.0,
    }