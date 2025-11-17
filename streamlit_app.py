# streamlit_app.py (or app.py)

import ast
import pandas as pd
import streamlit as st

# --------------------------------------------------
# Basic page config
# --------------------------------------------------
st.set_page_config(page_title="TOP-250 Movies Explorer", layout="wide")

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


# --------------------------------------------------
# Helper functions
# --------------------------------------------------
def parse_str_list(cell):
    """
    Parse list-like cells into a list of strings.

    Handles:
    - real Python lists
    - stringified lists like "['A', 'B']"
    - simple comma-separated strings like "A, B, C"
    """
    if isinstance(cell, list):
        return [str(x).strip(" '\"") for x in cell]

    if cell is None:
        return []
    try:
        if pd.isna(cell):
            return []
    except TypeError:
        pass

    text = str(cell).strip()
    if not text:
        return []

    if (text.startswith("[") and text.endswith("]")) or (
        text.startswith("(") and text.endswith(")")
    ):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple)):
                return [str(x).strip(" '\"") for x in parsed]
        except Exception:
            pass

    return [item.strip() for item in text.split(",") if item.strip()]


def ensure_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure numeric types and parse list-like columns."""
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
    """
    Return three DataFrames:
    - screentime_top10: top actors by total duration
    - most_active_top10: top actors by number of movies
    - most_gross_top10: top actors by total gross
    """
    df_cast = df.explode("castList").rename(columns={"castList": "actor"})
    df_cast = df_cast.dropna(subset=["actor"])
    df_cast["actor"] = df_cast["actor"].astype(str).str.strip()

    # Top by screentime
    screentime = (
        df_cast.groupby("actor")["duration"]
        .sum(min_count=1)
        .sort_values(ascending=False)
        .reset_index()
    )
    screentime_top10 = screentime.head(10).rename(columns={"duration": "total_duration"})

    # Top by number of movies
    most_active = (
        df_cast.groupby("actor")["title"]
        .nunique()
        .sort_values(ascending=False)
        .reset_index()
    )
    most_active_top10 = most_active.head(10).rename(columns={"title": "movie_count"})

    # Top by total gross
    most_gross = (
        df_cast.groupby("actor")["gross"]
        .sum(min_count=1)
        .sort_values(ascending=False)
        .reset_index()
    )
    most_gross_top10 = most_gross.head(10).rename(columns={"gross": "total_gross"})

    return screentime_top10, most_active_top10, most_gross_top10


# --------------------------------------------------
# UI
# --------------------------------------------------
st.title("TOP-250 Movies Explorer")

st.write(
    "Upload a CSV or JSON file containing the TOP-250 movies. "
    "Required columns: `url, title, ratingValue, ratingCount, year, description, "
    "budget, gross, duration, genreList, countryList, castList, characterList, directorList`."
)

uploaded_file = st.file_uploader(
    "Upload TOP-250 Movies file (CSV or JSON)", type=["csv", "json"]
)

if uploaded_file is None:
    st.info("👆 Please upload a CSV or JSON file to begin.")
    st.stop()

# --------------------------------------------------
# Read file
# --------------------------------------------------
if uploaded_file.name.lower().endswith(".csv"):
    df_raw = pd.read_csv(uploaded_file)
else:
    df_raw = pd.read_json(uploaded_file)

missing_cols = [c for c in EXPECTED_COLUMNS if c not in df_raw.columns]
if missing_cols:
    st.error(f"Missing required columns: {', '.join(missing_cols)}")
    st.stop()

df_raw = df_raw[EXPECTED_COLUMNS]
df = ensure_dtypes(df_raw)

# Show original data
st.subheader("Uploaded Data")
st.dataframe(df, use_container_width=True)

# --------------------------------------------------
# Precomputed query results
# --------------------------------------------------
# 1) Patience: duration >= 220 min
patience_df = df[df["duration"] >= 220].sort_values("duration", ascending=False)

# 2) Spielberg: total duration of all Spielberg movies
df_directors = df.explode("directorList").rename(columns={"directorList": "director"})
spielberg_df = df_directors[
    df_directors["director"].str.lower() == "steven spielberg"
].copy()
spielberg_total_duration = spielberg_df["duration"].sum()

# 3–5) Actor tables
screentime_top10, most_active_top10, most_gross_top10 = compute_actor_tables(df)

# 6) Timeline data: movies per year
year_counts = (
    df.groupby("year")["title"]
    .nunique()
    .reset_index(name="movie_count")
    .sort_values("year")
)

# --------------------------------------------------
# Tabs (including WOW: Timeline View)
# --------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Patience",
        "Binge Watching Steven Spielberg",
        "This is about me",
        "Workhorse",
        "Cash horse",
        "Timeline View ⭐",
    ]
)

# --- Tab 1: Patience ---
with tab1:
    st.subheader("Patience: Movies ≥ 220 minutes")
    st.write(
        "All movies with a duration above or equal to **220 minutes**, "
        "ordered by duration (descending)."
    )
    if patience_df.empty:
        st.warning("No movies with duration ≥ 220 minutes found.")
    else:
        st.dataframe(
            patience_df[
                [
                    "title",
                    "year",
                    "duration",
                    "ratingValue",
                    "ratingCount",
                    "directorList",
                    "castList",
                ]
            ],
            use_container_width=True,
        )

# --- Tab 2: Binge Watching Steven Spielberg ---
with tab2:
    st.subheader("Binge Watching Steven Spielberg")
    if spielberg_df.empty:
        st.warning("No movies directed by Steven Spielberg found.")
    else:
        if pd.notna(spielberg_total_duration):
            total_minutes = int(spielberg_total_duration)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            st.markdown(
                f"**Total duration of all movies directed by Steven Spielberg:** "
                f"{total_minutes} minutes (~{hours}h {minutes}m)"
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
        screentime_ranked = screentime_top10.assign(
            rank=lambda d: range(1, len(d) + 1)
        )
        st.dataframe(
            screentime_ranked[["rank", "actor", "total_duration"]],
            use_container_width=True,
        )

# --- Tab 4: Workhorse (Most active actors) ---
with tab4:
    st.subheader("Workhorse: TOP-10 most active actors")
    st.write(
        "Ranked by the **number of distinct movies** they have starred in."
    )
    if most_active_top10.empty:
        st.warning("No cast information available to compute activity.")
    else:
        active_ranked = most_active_top10.assign(
            rank=lambda d: range(1, len(d) + 1)
        )
        st.dataframe(
            active_ranked[["rank", "actor", "movie_count"]],
            use_container_width=True,
        )

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
        gross_ranked = most_gross_top10.assign(
            rank=lambda d: range(1, len(d) + 1)
        )
        st.dataframe(
            gross_ranked[["rank", "actor", "total_gross"]],
            use_container_width=True,
        )

# --- Tab 6: Timeline View (WOW Feature) ---
with tab6:
    st.subheader("Timeline View: Number of movies per year ⭐")
    st.write("A simple timeline showing how many TOP-250 movies were released each year.")

    if year_counts.empty:
        st.warning("No year information available to build the timeline.")
    else:
        # Use year as index for a clean bar chart
        st.bar_chart(
            year_counts.set_index("year")["movie_count"],
            use_container_width=True,
        )

        st.caption("Bars show how many of the uploaded TOP-250 movies belong to each year.")
