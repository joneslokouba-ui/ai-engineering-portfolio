"""Column-name helpers for the CER medallion pipeline.

Delta tables do not allow spaces or characters such as parentheses in column names, so
raw CSV headers are normalized once at the bronze layer. The same functions are copied
into notebook 01 so it runs on Databricks without installing this package.
"""
import re


def normalize_name(name) -> str:
    """Lowercase; every run of non-alphanumeric characters becomes one underscore."""
    cleaned = re.sub(r"[^0-9a-z]+", "_", str(name).strip().lower()).strip("_")
    return cleaned or "column"


def make_unique(names) -> list:
    """Keep column order; add a numeric suffix to repeated names (name, name_2, name_3)."""
    seen = {}
    result = []
    for name in names:
        if name in seen:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 1
            result.append(name)
    return result