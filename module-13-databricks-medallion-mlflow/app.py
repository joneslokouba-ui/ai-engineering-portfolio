"""Module 13 - CER Pipeline Incidents: medallion pipeline dashboard.

Streamlit companion to the Databricks notebooks. The notebooks build bronze, silver and
gold Delta tables from the Canada Energy Regulator (CER) Pipeline Incidents open dataset
(Open Government Licence - Canada). This app reads CSV exports of the gold tables from
the data/ folder:

    gold_kpis.csv, gold_incidents_by_year_province.csv, gold_release_by_substance.csv,
    gold_incident_types_by_year.csv, gold_causes.csv, gold_top_companies.csv,
    gold_significant_by_year.csv, gold_incident_locations.csv

The model tab reads data/model_metrics.json once the MLflow notebooks have been run.
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
GOLD_FILES = [
    "gold_kpis",
    "gold_incidents_by_year_province",
    "gold_release_by_substance",
    "gold_incident_types_by_year",
    "gold_causes",
    "gold_top_companies",
    "gold_significant_by_year",
    "gold_incident_locations",
]

st.set_page_config(page_title="CER Pipeline Incidents - Medallion Pipeline", layout="wide")


@st.cache_data
def load_csv(name: str):
    path = DATA_DIR / f"{name}.csv"
    return pd.read_csv(path) if path.exists() else None


st.title("CER Pipeline Incidents: Medallion Pipeline Dashboard")
st.caption(
    "Module 13 - Databricks lakehouse. Data: Canada Energy Regulator, Pipeline Incidents "
    "(Open Government Licence - Canada). Built from gold Delta tables produced by a "
    "bronze, silver and gold pipeline; this app reads exported snapshots of those tables."
)

missing = [name for name in GOLD_FILES if not (DATA_DIR / f"{name}.csv").exists()]
if missing:
    st.error("Missing data files in the data/ folder: " + ", ".join(f"{m}.csv" for m in missing))
    st.stop()

kpis = load_csv("gold_kpis").iloc[0]
by_year_province = load_csv("gold_incidents_by_year_province")
release = load_csv("gold_release_by_substance")
types_by_year = load_csv("gold_incident_types_by_year")
causes = load_csv("gold_causes")
companies = load_csv("gold_top_companies")
significant = load_csv("gold_significant_by_year")
locations = load_csv("gold_incident_locations")

# ---------- Sidebar filters ----------
year_min, year_max = int(by_year_province["year"].min()), int(by_year_province["year"].max())
years = st.sidebar.slider("Years", year_min, year_max, (year_min, year_max))
all_provinces = sorted(by_year_province["province"].dropna().unique())
provinces = st.sidebar.multiselect("Province or state", all_provinces, default=all_provinces)
st.sidebar.caption(
    "Year and province filters apply to the Overview, Significant and Map tabs. "
    "Release, cause and company tables are totals across all years."
)

in_years = by_year_province["year"].between(*years)
selected = by_year_province[in_years & by_year_province["province"].isin(provinces)]

tab_overview, tab_release, tab_causes, tab_sig, tab_map, tab_pipeline, tab_model = st.tabs(
    ["Overview", "Releases", "Causes and companies", "Significant incidents", "Map",
     "Pipeline", "Model"]
)

# ---------- Overview ----------
with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Incidents in selection", f"{int(selected['incidents'].sum()):,}")
    c2.metric("All incidents", f"{int(kpis['total_incidents']):,}")
    c3.metric("With a release substance", f"{int(kpis['incidents_with_release_substance']):,}")
    c4.metric("With a numeric volume", f"{int(kpis['incidents_with_numeric_volume']):,}")

    st.subheader("Incidents per year by province")
    per_year = selected.pivot_table(
        index="year", columns="province", values="incidents", aggfunc="sum", fill_value=0
    )
    if per_year.empty:
        st.info("No incidents for the current filter.")
    else:
        st.bar_chart(per_year)
    st.caption(
        "The province field includes one US state (Maine) for cross-border pipelines. "
        f"The latest year ({year_max}) is a partial year because the data is a snapshot."
    )

    st.subheader("Incident types by year")
    types_in_years = types_by_year[types_by_year["year"].between(*years)]
    top_types = (
        types_in_years.groupby("incident_types")["incidents"].sum().nlargest(6).index.tolist()
    )
    grouped_types = types_in_years.assign(
        incident_types=types_in_years["incident_types"].where(
            types_in_years["incident_types"].isin(top_types), "Other combinations"
        )
    )
    types_chart = grouped_types.pivot_table(
        index="year", columns="incident_types", values="incidents",
        aggfunc="sum", fill_value=0,
    )
    st.bar_chart(types_chart)
    st.caption(
        "The six most common incident type combinations are shown; all others are grouped "
        "as 'Other combinations' so each bar matches that year's incident count."
    )

# ---------- Releases ----------
with tab_release:
    st.subheader("Release volume by substance")
    min_incidents = st.slider("Minimum incidents per substance", 1, 20, 5)
    shown = release[release["incidents"] >= min_incidents].copy()
    for col in ["median_volume_m3", "total_volume_m3", "max_volume_m3"]:
        shown[col] = shown[col].round(3)
    st.dataframe(
        shown.sort_values("incidents", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
    st.bar_chart(shown.set_index("release_substance")["incidents"])
    st.caption(
        "Only incidents with a numeric volume feed the median, total and maximum "
        "(see incidents_with_volume). Volumes are as reported in cubic metres; gases and "
        "liquids may be reported on different bases, so compare within a substance rather "
        "than across substances. Incidents with no release are excluded."
    )

# ---------- Causes and companies ----------
with tab_causes:
    left, right = st.columns(2)
    for column, dimension in ((left, "What happened"), (right, "Why it happened")):
        with column:
            st.subheader(dimension)
            part = causes[causes["dimension"] == dimension].nlargest(10, "incidents")
            st.bar_chart(part.set_index("category")["incidents"])
    st.subheader("Companies with the most incidents")
    st.dataframe(companies.head(15), use_container_width=True, hide_index=True)

# ---------- Significant incidents ----------
with tab_sig:
    st.subheader("Significant incidents by year")
    sig = significant[significant["year"].between(*years)]
    st.line_chart(sig.set_index("year")["significant_rate"])
    st.dataframe(sig, use_container_width=True, hide_index=True)
    st.caption(
        "Significant rate = significant incidents divided by incidents with a readable "
        "significant flag. This flag is the target of the Module 13 model."
    )

# ---------- Map ----------
with tab_map:
    st.subheader("Incident locations")
    points = locations[
        locations["year"].between(*years) & locations["province"].isin(provinces)
    ].dropna(subset=["latitude", "longitude"])
    st.caption(f"{len(points):,} incidents with coordinates in the current selection.")
    if points.empty:
        st.info("No located incidents for the current filter.")
    else:
        st.map(points[["latitude", "longitude"]])

# ---------- Pipeline ----------
with tab_pipeline:
    st.subheader("Medallion layers")
    st.markdown(
        """
| Layer | Tables | Purpose |
|---|---|---|
| Bronze | `cer_bronze` | Raw CER CSV loaded as text into a Delta table; only column names normalized |
| Silver | `cer_silver` | Typed dates, numbers and counts; standardized fields and company names; duplicates removed; parse failures counted |
| Data quality | `cer_dq_results` | 14 checks (4 error, 10 warn) with results kept over time and a gate that stops on errors |
| Gold | 8 `gold_*` tables | Aggregates for this dashboard and the Databricks dashboard |
| Model | MLflow experiment | Models predicting the `significant` flag |
"""
    )
    st.markdown(
        "Notebooks: `01_bronze_ingest`, `02_silver_clean`, `03_data_quality`, "
        "`04_gold_aggregates`, `05_features_and_model`, `06_register_and_score`."
    )

# ---------- Model ----------
with tab_model:
    st.subheader("Model results")
    metrics_path = DATA_DIR / "model_metrics.json"
    if not metrics_path.exists():
        st.info("Model results will appear here once the MLflow notebooks have been run.")
    else:
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            st.dataframe(
                pd.DataFrame(metrics["models"]), use_container_width=True, hide_index=True
            )
            if metrics.get("notes"):
                st.caption(metrics["notes"])
            st.caption(
                "Reading the results: the reporting_time feature set includes incident "
                "type and substance, which are only known once an incident has been "
                "reported, so its scores describe classification at reporting time, not "
                "a forecast made beforehand. The context_only models (test PR-AUC about "
                "0.40 to 0.42 against a 0.24 baseline) show what can be predicted "
                "without those fields."
                "For the baseline, precision, recall and F1 are 0 because it never predicts "
                "a significant incident at the 0.5 threshold. "
            )
        except (ValueError, KeyError) as exc:
            st.error(f"Could not read model_metrics.json: {exc}")

st.caption(
    "Source: Canada Energy Regulator, Pipeline Incidents, Open Government Licence - Canada. "
    "Figures come from a downloaded snapshot of the dataset."
)