"""Module 12 - CER Pipeline Incidents.

Streamlit view of the Databricks lakehouse work. Reads a snapshot of the
Canada Energy Regulator (CER) Pipeline Incidents open dataset, published under
the Open Government Licence - Canada, and reproduces the main views of the
Databricks dashboard: total incidents, incidents per year by province, and
median release volume by substance.
"""
import re
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent / "data" / "pipeline-incidents-data.csv"
MIN_INCIDENTS = 5  # substances need at least this many incidents in the median table
REQUIRED = ["incident_number", "province", "year", "substance", "approximate_volume_released_m3"]

st.set_page_config(page_title="CER Pipeline Incidents", layout="wide")


def normalize(name: str) -> str:
    """Lowercase and replace non-alphanumerics with underscores (matches the Spark table names)."""
    return re.sub(r"[^0-9a-z]+", "_", str(name).strip().lower()).strip("_")


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=encoding, low_memory=False)
            break
        except UnicodeDecodeError:
            continue
    if df is None:
        raise ValueError("Could not decode the CSV file.")
    df.columns = [normalize(c) for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    return df


st.title("CER Pipeline Incidents")
st.caption(
    "Module 12 - Databricks lakehouse. Data: Canada Energy Regulator, Pipeline Incidents "
    "(Open Government Licence - Canada). This app reads a downloaded snapshot of the dataset."
)

if not DATA_PATH.exists():
    st.error(f"Data file not found: {DATA_PATH.name}. Place it in the app's data/ folder.")
    st.stop()

df = load_data(DATA_PATH)

missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    st.error(f"Missing expected columns: {missing}")
    st.write("Columns found:", list(df.columns))
    st.stop()

df["year"] = pd.to_numeric(df["year"], errors="coerce")
# The volume column is text in the source; only some rows hold a usable number.
df["volume_m3"] = pd.to_numeric(df["approximate_volume_released_m3"], errors="coerce")

provinces = sorted(df["province"].dropna().unique())
selected = st.sidebar.multiselect("Province", provinces, default=provinces)
view = df[df["province"].isin(selected)]

col1, col2, col3 = st.columns(3)
col1.metric("Total incidents", f"{view['incident_number'].nunique():,}")
col2.metric("Provinces shown", len(selected))
col3.metric("Incidents with a numeric volume", f"{view['volume_m3'].notna().sum():,}")

st.subheader("Incidents per year by province")
per_year = (
    view.dropna(subset=["year"])
    .assign(year=lambda d: d["year"].astype(int))
    .pivot_table(
        index="year",
        columns="province",
        values="incident_number",
        aggfunc="nunique",
        fill_value=0,
    )
)
if per_year.empty:
    st.info("No incidents for the current filter.")
else:
    st.bar_chart(per_year)

st.subheader(f"Median release volume by substance (substances with {MIN_INCIDENTS}+ incidents)")
by_substance = (
    view.dropna(subset=["substance"])
    .groupby("substance")
    .agg(
        incidents=("incident_number", "nunique"),
        incidents_with_volume=("volume_m3", "count"),
        median_release_m3=("volume_m3", "median"),
    )
    .query("incidents >= @MIN_INCIDENTS and incidents_with_volume > 0")
    .sort_values("median_release_m3", ascending=False)
    .reset_index()
)
if by_substance.empty:
    st.info("No substance meets the minimum incident count for the current filter.")
else:
    st.dataframe(by_substance, use_container_width=True, hide_index=True)

st.caption(
    "Notes: volume is reported as text in the source and only some incidents have a numeric "
    "value, so medians use those incidents only. See the Module 12 README for the Databricks "
    "dashboard this app mirrors."
)