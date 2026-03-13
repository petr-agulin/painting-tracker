import streamlit as st
from database import initialize_database, get_connection

initialize_database()

st.set_page_config(
    page_title="Painting Tracker",
    page_icon="🎨",
    layout="wide"
)

st.title("🎨 Painting Tracker")

st.markdown("""
**Painting Tracker** is a personal journal for watercolor artists who want to paint more intentionally.

Most painters finish a session and move on. Over time, the details fade — which colors you mixed, what worked, what frustrated you, how long things actually took. This tool captures all of that, session by session, so nothing is lost.

**What you can do here:**
Log every painting from first brushstroke to finished work. Record your techniques, colors, mood, and reflections after each session. Build a visual archive of your progress with photos. Discover patterns in your creative process — when you paint best, which conditions produce your strongest work, how your skills develop over time.

**How to get started:**
Start by adding your paints in **My Palette** — search by brand and tube number. Then add your first painting in **Manage Paintings**. After each session, log it in **Manage Sessions**. Over time, visit the **Dashboard** to see what your data reveals about you as a painter.

**Your data stays on your computer.** Nothing is sent anywhere. You own it completely.
""")

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

conn.close()