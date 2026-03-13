import streamlit as st
from database import get_connection
from datetime import datetime

st.set_page_config(page_title="Next Up", page_icon="🎯")
st.title("🎯 What to Work on Next")
st.markdown("""
All paintings currently in progress, sorted by how long since your last session. Use this as your daily prompt — the painting at the top is the one you have left waiting the longest.
""")

conn = get_connection()

st.subheader("In-progress paintings")
st.markdown("Sorted by how long since your last session.")

paintings = conn.execute("""
    SELECT p.*,
        MAX(s.date) as last_session_date,
        COUNT(s.id) as session_count,
        SUM(s.duration_minutes) as total_minutes,
        MAX(s.completion_percent) as latest_completion,
        MAX(s.image_path) as latest_image
    FROM paintings p
    LEFT JOIN sessions s ON s.painting_id = p.id
    WHERE p.status = 'In progress'
    GROUP BY p.id
    ORDER BY last_session_date ASC
""").fetchall()

if not paintings:
    st.info("No in-progress paintings. Add a painting and set its status to In progress.")
else:
    for painting in paintings:
        days_since = None
        if painting["last_session_date"]:
            try:
                last = datetime.strptime(painting["last_session_date"], "%Y-%m-%d")
                days_since = (datetime.today() - last).days
            except Exception:
                pass

        label = f"🖼️ {painting['title']}"
        if days_since is not None:
            label += f" — last session {days_since} days ago"
        else:
            label += " — no sessions yet"

        with st.expander(label):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Sessions:** {painting['session_count'] or 0}")
                total_hours = (painting["total_minutes"] or 0) // 60
                total_mins = (painting["total_minutes"] or 0) % 60
                st.write(f"**Total time:** {total_hours}h {total_mins}m")
                st.write(f"**Completion:** {painting['latest_completion'] or 0}%")
                st.write(f"**Genre:** {painting['genre'] or 'not set'}")
                st.write(f"**Style:** {painting['style'] or 'not set'}")
            with col2:
                if painting["latest_image"]:
                    st.image(painting["latest_image"], caption="Last session photo", width=250)

            last_session = conn.execute("""
                SELECT whats_next FROM sessions
                WHERE painting_id = ?
                ORDER BY date DESC LIMIT 1
            """, (painting["id"],)).fetchone()

            if last_session and last_session["whats_next"]:
                st.markdown(f"**Next step noted:** {last_session['whats_next']}")

st.markdown("---")
st.subheader("🏆 Personal Records")

total_paintings = conn.execute("SELECT COUNT(*) as c FROM paintings").fetchone()["c"]
total_sessions = conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]
total_minutes = conn.execute("SELECT SUM(duration_minutes) as t FROM sessions").fetchone()["t"] or 0
best_session = conn.execute("SELECT MAX(rating) as r FROM sessions").fetchone()["r"]
longest_session = conn.execute("SELECT MAX(duration_minutes) as m FROM sessions").fetchone()["m"] or 0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total paintings", total_paintings)
    st.metric("Best session rating", f"{best_session}/5" if best_session else "none yet")
with col2:
    st.metric("Total sessions", total_sessions)
    st.metric("Longest session", f"{longest_session} min")
with col3:
    st.metric("Total hours painted", f"{total_minutes // 60}h {total_minutes % 60}m")

sessions_by_date = conn.execute("""
    SELECT date, COUNT(*) as count
    FROM sessions
    GROUP BY date
    ORDER BY date
""").fetchall()

if sessions_by_date:
    dates = [s["date"] for s in sessions_by_date]
    streak = 1
    best_streak = 1
    for i in range(1, len(dates)):
        try:
            d1 = datetime.strptime(dates[i-1], "%Y-%m-%d")
            d2 = datetime.strptime(dates[i], "%Y-%m-%d")
            if (d2 - d1).days == 1:
                streak += 1
                best_streak = max(best_streak, streak)
            else:
                streak = 1
        except Exception:
            pass
    st.metric("Best consecutive painting streak", f"{best_streak} days")

conn.close()