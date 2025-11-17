import ast
import streamlit as st
import pandas as pd

# ---------- Page config ----------
st.set_page_config(
    page_title="TOP-250 Movies Explorer",
    layout="wide",
)

# ---------- Minimalistic styling ----------
MINIMAL_CSS = """
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
</style>
"""
st.markdown(MINIMAL_CSS, unsafe_allow_html=True)

st.title("TOP-250 Movies Explorer")

st.write(
    "Upload a CSV or JSON file containing the TOP-250 movies. "
    "Required columns: `url, title, ratingValue, ratingCount, year, description, "
    "budget, gross, duration, genreList, countryList, castList, characterList, directorList`."
)

# ---------- Helper functions ----------

EXPECTED_COLUMNS = [
    "url",
    "title",
    "ratingValue",
    "ratingCount",
    "year",
    "description",
    "budget",
    "gross",
    "duration",
    "genreList",
    "countryList",
    "castList",
    "characterList",
    "directorList",
]


def parse_str_list(cell):
    """Parse a cell that should represent a list of strings.

    Handles:
    - real Python lists
    - stringified lists like "['A', 'B']"
    - simple comma-separated strings like "A, B, C"
    """
    if pd.isna(cell):
        return []
    if isinstance(cell, list):
        return cell

    text = str(cell).strip()
    # Try literal_eval if it looks like a list
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return [str(x).strip(" '\"") for x in parsed]
        except Exception:
            pass

    # Fallback: treat as comma-separated
    return [item.strip() for item in text.split(",") if item.strip()]


def ensure_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Convert numeric columns and parse list-like columns."""
    df = df.copy()

    # Numeric columns
    for col in ["duration", "gross", "budget", "ratingValue", "ratingCount", "year"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # List-like columns
    for col in ["castList", "directorList", "genreList", "countryList", "characterList"]:
        if col in df.columns:
            df[col] = df[col].apply(parse_str_list)

    return df


def compute_actor_tables(df: pd.DataFrame):
    """Return three DataFrames:
    - screentime_top10
    - most_active_top10
    - most_gross_top10
    """
    # Explode cast
    df_cast = df.explode("castList")
    df_cast = df_cast.rename(columns={"castList": "actor"})
    df_cast = df_cast.dropna(subset=["actor"])
    df_cast["actor"] = df_cast["actor"].astype(str).str.strip()

    # 1) Screentime: total duration per actor
    screentime = (
        df_cast.groupby("actor")["duration"]
        .sum(min_count=1)
        .sort_values(ascending=False)
        .reset_index()
    )
    screentime_top10 = screentime.head(10).rename(columns={"duration": "total_duration"})

    # 2) Most active: number of movies per actor
    most_active = (
        df_cast.groupby("actor")["title"]
        .nunique()
        .sort_values(ascending=False)
        .reset_index()
    )
    most_active_top10 = most_active.head(10).rename(columns={"title": "movie_count"})

    # 3) Most gross: total gross per actor
    most_gross = (
        df_cast.groupby("actor")["gross"]
        .sum(min_count=1)
        .sort_values(ascending=False)
        .reset_index()
    )
    most_gross_top10 = most_gross.head(10).rename(columns={"gross": "total_gross"})

    return screentime_top10, most_active_top10, most_gross_top10


# ---------- File upload ----------
uploaded_file = st.file_uploader(
    "Upload TOP-250 Movies file (CSV or JSON)", type=["csv", "json"]
)

if uploaded_file is None:
    st.info("👆 Please upload a CSV or JSON file to begin.")
    st.stop()

# ---------- Read data ----------
if uploaded_file.name.lower().endswith(".csv"):
    df_raw = pd.read_csv(uploaded_file)
else:  # JSON
    # Assume JSON is records or normal table-like structure
    df_raw = pd.read_json(uploaded_file)

# Ensure required columns exist
missing_cols = [c for c in EXPECTED_COLUMNS if c not in df_raw.columns]
if missing_cols:
    st.error(f"Missing required columns: {', '.join(missing_cols)}")
    st.stop()

# Reorder columns to expected order
df_raw = df_raw[EXPECTED_COLUMNS]

# Type & list parsing
df = ensure_dtypes(df_raw)

# ---------- Show raw data ----------
st.subheader("Uploaded Data")
st.dataframe(df, use_container_width=True)

# ---------- Precomputed views ----------
# Patience: duration >= 220 minutes
patience_df = df[df["duration"] >= 220].sort_values("duration", ascending=False)

# Spielberg movies
df_directors = df.explode("directorList").rename(columns={"directorList": "director"})
spielberg_df = df_directors[
    df_directors["director"].str.lower() == "steven spielberg"
].copy()
spielberg_total_duration = spielberg_df["duration"].sum()

# Actor-based tables
screentime_top10, most_active_top10, most_gross_top10 = compute_actor_tables(df)

# ---------- Tabs ----------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Patience",
        "Binge Watching Steven Spielberg",
        "This is about me",
        "Workhorse",
        "Cash horse",
    ]
)

# --- Tab 1: Patience ---
with tab1:
    st.subheader("Patience: Movies ≥ 220 minutes")
    st.write(
        "All movies with a duration above or equal to **220 minutes** "
        "ordered by duration (descending)."
    )
    if patience_df.empty:
        st.warning("No movies with duration ≥ 220 minutes found.")
    else:
        st.dataframe(
            patience_df[
                ["title", "year", "duration", "ratingValue", "ratingCount", "directorList", "castList"]
            ],
            use_container_width=True,
        )

# --- Tab 2: Binge Watching Steven Spielberg ---
with tab2:
    st.subheader("Binge Watching Steven Spielberg")
    if spielberg_df.empty:
        st.warning("No movies directed by Steven Spielberg found.")
    else:
        total_hours = spielberg_total_duration // 60 if pd.notna(spielberg_total_duration) else 0
        leftover_minutes = spielberg_total_duration % 60 if pd.notna(spielberg_total_duration) else 0

        st.markdown(
            f"**Total duration of all movies directed by Steven Spielberg:** "
            f"{spielberg_total_duration:.0f} minutes "
            f"(~{int(total_hours)}h {int(leftover_minutes)}m)"
        )

        st.dataframe(
            spielberg_df[
                ["title", "year", "duration", "ratingValue", "ratingCount", "castList"]
            ].sort_values("year"),
            use_container_width=True,
        )

# --- Tab 3: This is about me (Top-10 by screentime) ---
with tab3:
    st.subheader("This is about me: TOP-10 actors by screentime")
    st.write(
        "Ranked by the **sum of durations** of all movies they star in."
    )

    if screentime_top10.empty:
        st.warning("No cast information available to compute screentime.")
    else:
        screentime_top10 = screentime_top10.copy()
        screentime_top10.insert(0, "rank", range(1, len(screentime_top10) + 1))
        st.dataframe(screentime_top10, use_container_width=True)

# --- Tab 4: Workhorse (Most active actors) ---
with tab4:
    st.subheader("Workhorse: TOP-10 most active actors")
    st.write(
        "Ranked by the **number of distinct movies** they have starred in."
    )

    if most_active_top10.empty:
        st.warning("No cast information available to compute activity.")
    else:
        most_active_top10 = most_active_top10.copy()
        most_active_top10.insert(0, "rank", range(1, len(most_active_top10) + 1))
        st.dataframe(most_active_top10, use_container_width=True)

# --- Tab 5: Cash horse (Most successful actors by gross) ---
with tab5:
    st.subheader("Cash horse: TOP-10 actors by total gross")
    st.write(
        "Ranked by the **sum of gross** of all movies they star in. "
        "Each actor is credited with the full movie gross."
    )

    if most_gross_top10.empty:
        st.warning("No cast or gross information available to compute totals.")
    else:
        most_gross_top10 = most_gross_top10.copy()
        most_gross_top10.insert(0, "rank", range(1, len(most_gross_top10) + 1))
        st.dataframe(most_gross_top10, use_container_width=True)
