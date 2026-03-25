import streamlit as st
from database import get_connection
import plotly.express as px
import pandas as pd
from datetime import datetime as dt

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Insights Dashboard")
st.markdown("""
Discover patterns in your painting habits. Charts update automatically as you log more sessions — the more data you have, the more useful this becomes.
""")

conn = get_connection()

paintings = pd.read_sql("SELECT * FROM paintings", conn)
sessions = pd.read_sql("SELECT * FROM sessions", conn)

if sessions.empty:
    st.info("No session data yet. Log some sessions to see your insights.")
    st.stop()

sessions["duration_minutes"] = pd.to_numeric(sessions["duration_minutes"], errors="coerce")
sessions["rating"] = pd.to_numeric(sessions["rating"], errors="coerce")
sessions["date"] = pd.to_datetime(sessions["date"], errors="coerce")

st.markdown("---")
st.subheader("Overview")
total_hours = int(sessions["duration_minutes"].sum() // 60)
longest_session = int(sessions["duration_minutes"].max())

sessions_sorted = sessions.dropna(subset=["date"]).copy().sort_values("date")
dates = sessions_sorted["date"].dt.strftime("%Y-%m-%d").tolist()
best_streak = 1
streak = 1
for i in range(1, len(dates)):
    try:
        d1 = dt.strptime(dates[i-1], "%Y-%m-%d")
        d2 = dt.strptime(dates[i], "%Y-%m-%d")
        if (d2 - d1).days == 1:
            streak += 1
            best_streak = max(best_streak, streak)
        else:
            streak = 1
    except Exception:
        pass

now = pd.Timestamp.now()
this_month = sessions_sorted[
    (sessions_sorted["date"].dt.year == now.year) &
    (sessions_sorted["date"].dt.month == now.month)
]
last_month_date = now - pd.DateOffset(months=1)
last_month = sessions_sorted[
    (sessions_sorted["date"].dt.year == last_month_date.year) &
    (sessions_sorted["date"].dt.month == last_month_date.month)
]
avg_dur_this = this_month["duration_minutes"].mean() if not this_month.empty else None
avg_dur_last = last_month["duration_minutes"].mean() if not last_month.empty else None
dur_delta = None
if avg_dur_this is not None and avg_dur_last is not None:
    dur_delta = round(avg_dur_this - avg_dur_last)

avg_dur_label = f"{round(avg_dur_this)} min" if avg_dur_this is not None else "no data"
dur_delta_label = f"{dur_delta:+d} min vs last month" if dur_delta is not None else None

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Total Paintings", len(paintings))
with col2:
    st.metric("Total Sessions", len(sessions))
with col3:
    st.metric("Total Hours", total_hours)
with col4:
    st.metric("Avg Duration This Month", avg_dur_label, delta=dur_delta_label)
with col5:
    st.metric("Longest Session", f"{longest_session} min")
with col6:
    st.metric("Best Streak", f"{best_streak} days")

st.markdown("---")
st.subheader("Stats")

st.markdown("#### Session ratings over time")
fig1 = px.scatter(
    sessions, x="date", y="rating",
    trendline="lowess",
    labels={"date": "Date", "rating": "Rating"},
    color_discrete_sequence=["#7B9E87"]
)
st.plotly_chart(fig1, use_container_width=True)

if "mental_state" in sessions.columns:
    mood_ratings = sessions.groupby("mental_state")["rating"].mean().reset_index()
    mood_ratings.columns = ["Mental State", "Average Rating"]
    mood_ratings = mood_ratings.dropna()
    if not mood_ratings.empty:
        st.markdown("#### Average rating by mental state")
        fig3 = px.bar(
            mood_ratings, x="Mental State", y="Average Rating",
            color_discrete_sequence=["#D4B896"]
        )
        st.plotly_chart(fig3, use_container_width=True)

if "techniques" in sessions.columns:
    all_techniques = sessions["techniques"].dropna().str.split(", ").explode()
    if not all_techniques.empty:
        technique_counts = all_techniques.value_counts().reset_index()
        technique_counts.columns = ["Technique", "Count"]
        st.markdown("#### Techniques used")
        fig4 = px.bar(
            technique_counts, x="Technique", y="Count",
            color_discrete_sequence=["#9B8EA8"]
        )
        st.plotly_chart(fig4, use_container_width=True)

merged = sessions.merge(paintings[["id", "inspiration_category"]], left_on="painting_id", right_on="id", how="left")
if "inspiration_category" in merged.columns:
    insp_ratings = merged.groupby("inspiration_category")["rating"].mean().reset_index()
    insp_ratings.columns = ["Inspiration Source", "Average Rating"]
    insp_ratings = insp_ratings.dropna()
    if not insp_ratings.empty:
        st.markdown("#### Average rating by inspiration source")
        fig5 = px.bar(
            insp_ratings, x="Inspiration Source", y="Average Rating",
            color_discrete_sequence=["#C4A882"]
        )
        st.plotly_chart(fig5, use_container_width=True)

sessions_with_date = sessions.dropna(subset=["date"]).copy()
sessions_with_date["year"] = sessions_with_date["date"].dt.year
sessions_with_date["month"] = sessions_with_date["date"].dt.month
sessions_with_date["month_label"] = sessions_with_date["date"].dt.strftime("%b")

available_years = sorted(sessions_with_date["year"].dropna().unique().tolist(), reverse=True)
if available_years:
    st.markdown("#### Sessions per month")
    col_year, _ = st.columns([1, 9])
    with col_year:
        selected_year = st.selectbox("Year", available_years, key="sessions_per_month_year", label_visibility="collapsed")
    year_data = sessions_with_date[sessions_with_date["year"] == selected_year]
    monthly_counts = (
        year_data.groupby(["month", "month_label"])
        .size()
        .reset_index(name="Sessions")
        .sort_values("month")
    )
    all_months = pd.DataFrame({
        "month": range(1, 13),
        "month_label": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    })
    monthly_counts = all_months.merge(monthly_counts, on=["month", "month_label"], how="left").fillna(0)
    monthly_counts["Sessions"] = monthly_counts["Sessions"].astype(int)
    fig_monthly = px.bar(
        monthly_counts, x="month_label", y="Sessions",
        labels={"month_label": "Month", "Sessions": "Sessions"},
        color_discrete_sequence=["#7B9E87"]
    )
    fig_monthly.update_layout(xaxis={"categoryorder": "array", "categoryarray": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]})
    st.plotly_chart(fig_monthly, use_container_width=True)

conn.close()