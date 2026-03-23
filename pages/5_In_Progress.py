import streamlit as st
from database import get_connection
from datetime import datetime
import os

st.set_page_config(page_title="In Progress", page_icon="🎯", layout="wide")
st.title("🎯 In Progress & Abandoned")

st.markdown("""
All paintings currently in progress or abandoned, sorted by how long since your last session. Use this as your daily prompt — the painting at the top is the one you have left waiting the longest.
""")

conn = get_connection()

paintings = conn.execute("""
    SELECT p.*,
        MAX(s.date) as last_session_date,
        COUNT(s.id) as session_count,
        SUM(s.duration_minutes) as total_minutes,
        MAX(s.completion_percent) as latest_completion
    FROM paintings p
    LEFT JOIN sessions s ON s.painting_id = p.id
    WHERE p.status IN ('In progress', 'Abandoned')
    GROUP BY p.id
    ORDER BY last_session_date ASC
""").fetchall()

if not paintings:
    st.info("No in-progress or abandoned paintings. Add a painting and set its status to In progress.")
else:
    for painting in paintings:
        days_since = None
        if painting["last_session_date"]:
            try:
                last = datetime.strptime(painting["last_session_date"], "%Y-%m-%d")
                days_since = (datetime.today() - last).days
            except Exception:
                pass

        label = f"{'🎨' if painting['status'] == 'In progress' else '⏸️'} {painting['title']} — {painting['status']}"
        if days_since is not None:
            if days_since == 0:
                label += " — last session today"
            elif days_since == 1:
                label += " — last session yesterday"
            elif days_since < 365:
                label += f" — last session {days_since} days ago"
            else:
                years = days_since // 365
                label += f" — last session {years} year{'s' if years > 1 else ''} ago"
        else:
            label += " — no sessions yet"

        with st.expander(label):
            col1, col2 = st.columns([1, 3])
            with col1:
                if painting["image_path"] and os.path.exists(painting["image_path"]):
                    st.image(painting["image_path"], width=120)
                else:
                    st.markdown(
                        '<div style="background:#f0f0f0;height:120px;width:120px;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#aaa;font-size:12px">No preview</div>',
                        unsafe_allow_html=True
                    )
            with col2:
                st.write(f"**Sessions:** {painting['session_count'] or 0}")
                total_hours = (painting["total_minutes"] or 0) // 60
                total_mins = (painting["total_minutes"] or 0) % 60
                st.write(f"**Total time:** {total_hours}h {total_mins}m")
                st.write(f"**Completion:** {painting['latest_completion'] or 0}%")
                st.write(f"**Genre:** {painting['genre'] or '—'}")
                st.write(f"**Style:** {painting['style'] or '—'}")

                if painting["date_started"]:
                    try:
                        started = datetime.strptime(painting["date_started"], "%Y-%m-%d")
                        days_started = (datetime.today() - started).days
                        if days_started < 365:
                            ago_text = f"{days_started} day{'s' if days_started != 1 else ''} ago"
                        else:
                            years = days_started // 365
                            ago_text = f"{years} year{'s' if years > 1 else ''} ago"
                        st.write(f"**Started:** {painting['date_started']} ({ago_text})")
                    except Exception:
                        st.write(f"**Started:** {painting['date_started']}")
                else:
                    st.write(f"**Started:** —")

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