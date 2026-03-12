import streamlit as st
from database import initialize_database, get_connection

initialize_database()

st.set_page_config(
    page_title="Painting Tracker",
    page_icon="🎨",
    layout="wide"
)

st.title("🎨 Painting Tracker")
st.markdown("Welcome to your personal watercolor painting journal.")
st.markdown("---")

conn = get_connection()

total_paintings = conn.execute("SELECT COUNT(*) as c FROM paintings").fetchone()["c"]
total_sessions = conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]
total_minutes = conn.execute("SELECT SUM(duration_minutes) as t FROM sessions").fetchone()["t"] or 0
total_hours = round(total_minutes / 60, 1)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Paintings", total_paintings)
with col2:
    st.metric("Total Sessions", total_sessions)
with col3:
    st.metric("Total Hours", total_hours)

st.markdown("---")
st.subheader("What would you like to do?")
st.markdown("Use the **sidebar on the left** to navigate between sections.")

conn.close()