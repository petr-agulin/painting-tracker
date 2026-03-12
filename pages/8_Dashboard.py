import streamlit as st
from database import get_connection
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Dashboard", page_icon="📊")
st.title("📊 Insights Dashboard")

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
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Paintings", len(paintings))
with col2:
    st.metric("Total Sessions", len(sessions))
with col3:
    total_hours = int(sessions["duration_minutes"].sum() // 60)
    st.metric("Total Hours", total_hours)
with col4:
    avg_rating = sessions["rating"].mean()
    st.metric("Avg Session Rating", f"{avg_rating:.1f}/5")

st.markdown("---")

st.subheader("Session ratings over time")
fig1 = px.scatter(
    sessions, x="date", y="rating",
    trendline="lowess",
    labels={"date": "Date", "rating": "Rating"},
    color_discrete_sequence=["#7B9E87"]
)
st.plotly_chart(fig1, use_container_width=True)

st.subheader("Session duration distribution")
fig2 = px.histogram(
    sessions, x="duration_minutes",
    nbins=20,
    labels={"duration_minutes": "Duration (minutes)"},
    color_discrete_sequence=["#B5C4B1"]
)
st.plotly_chart(fig2, use_container_width=True)

if "mental_state" in sessions.columns:
    mood_ratings = sessions.groupby("mental_state")["rating"].mean().reset_index()
    mood_ratings.columns = ["Mental State", "Average Rating"]
    mood_ratings = mood_ratings.dropna()
    if not mood_ratings.empty:
        st.subheader("Average rating by mental state")
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
        st.subheader("Techniques used")
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
        st.subheader("Average rating by inspiration source")
        fig5 = px.bar(
            insp_ratings, x="Inspiration Source", y="Average Rating",
            color_discrete_sequence=["#C4A882"]
        )
        st.plotly_chart(fig5, use_container_width=True)

if "completion_percent" in sessions.columns:
    completion = sessions.groupby("painting_id")["completion_percent"].max().reset_index()
    completion = completion.merge(paintings[["id", "title"]], left_on="painting_id", right_on="id")
    st.subheader("Completion progress per painting")
    fig6 = px.bar(
        completion, x="title", y="completion_percent",
        labels={"title": "Painting", "completion_percent": "Completion %"},
        color_discrete_sequence=["#A8C5B5"]
    )
    st.plotly_chart(fig6, use_container_width=True)

conn.close()