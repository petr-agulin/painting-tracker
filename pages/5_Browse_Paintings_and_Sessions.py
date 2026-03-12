import streamlit as st
from database import get_connection
import pandas as pd

st.set_page_config(page_title="Browse", page_icon="🔍")
st.title("🔍 Browse Paintings & Sessions")

conn = get_connection()

tab1, tab2 = st.tabs(["Paintings", "Sessions"])

with tab1:
    st.subheader("All Paintings")

    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Filter by status", ["All", "In progress", "Complete", "Abandoned", "Not started"])
    with col2:
        genre_filter = st.selectbox("Filter by genre", ["All"] + [
            row["genre"] for row in conn.execute(
                "SELECT DISTINCT genre FROM paintings WHERE genre != ''"
            ).fetchall()
        ])
    with col3:
        search = st.text_input("Search by title")

    query = "SELECT * FROM paintings WHERE 1=1"
    params = []

    if status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)
    if genre_filter != "All":
        query += " AND genre = ?"
        params.append(genre_filter)
    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    paintings = conn.execute(query, params).fetchall()

    if not paintings:
        st.info("No paintings found.")
    else:
        for painting in paintings:
            with st.expander(f"🖼️ {painting['title']} — {painting['status']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Genre:** {painting['genre'] or '—'}")
                    st.write(f"**Subject:** {painting['subject'] or '—'}")
                    st.write(f"**Style:** {painting['style'] or '—'}")
                    st.write(f"**Mood:** {painting['mood'] or '—'}")
                    st.write(f"**Paper:** {painting['paper_size'] or '—'} / {painting['paper_type'] or '—'}")
                with col2:
                    st.write(f"**Started:** {painting['date_started'] or '—'}")
                    st.write(f"**Finished:** {painting['date_finished'] or '—'}")
                    st.write(f"**Inspiration:** {painting['inspiration_category'] or '—'}")
                    st.write(f"**Note:** {painting['inspiration_note'] or '—'}")

                sessions = conn.execute(
                    "SELECT * FROM sessions WHERE painting_id = ? ORDER BY date",
                    (painting["id"],)
                ).fetchall()

                st.write(f"**Total sessions:** {len(sessions)}")

                if sessions:
                    total_minutes = sum(s["duration_minutes"] or 0 for s in sessions)
                    avg_rating = sum(s["rating"] or 0 for s in sessions) / len(sessions)
                    st.write(f"**Total time:** {total_minutes // 60}h {total_minutes % 60}m")
                    st.write(f"**Average session rating:** {avg_rating:.1f}/5")
                    latest = sessions[-1]
                    st.write(f"**Latest completion:** {latest['completion_percent'] or 0}%")
                    if latest["image_path"]:
                        st.image(latest["image_path"], caption="Latest session photo", width=300)

with tab2:
    st.subheader("All Sessions")

    col1, col2 = st.columns(2)
    with col1:
        rating_filter = st.selectbox("Filter by rating", ["All", "5", "4", "3", "2", "1"])
    with col2:
        state_filter = st.selectbox("Filter by mental state", ["All"] + [
            row["mental_state"] for row in conn.execute(
                "SELECT DISTINCT mental_state FROM sessions WHERE mental_state != ''"
            ).fetchall()
        ])

    query = """
        SELECT s.*, p.title as painting_title
        FROM sessions s
        JOIN paintings p ON s.painting_id = p.id
        WHERE 1=1
    """
    params = []

    if rating_filter != "All":
        query += " AND s.rating = ?"
        params.append(int(rating_filter))
    if state_filter != "All":
        query += " AND s.mental_state = ?"
        params.append(state_filter)

    query += " ORDER BY s.date DESC"
    sessions = conn.execute(query, params).fetchall()

    if not sessions:
        st.info("No sessions found.")
    else:
        for session in sessions:
            with st.expander(f"🎨 {session['painting_title']} — {session['date']} — Rating: {session['rating']}/5"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Duration:** {session['duration_minutes'] or 0} minutes")
                    st.write(f"**Location:** {session['location'] or '—'}")
                    st.write(f"**Lighting:** {session['lighting'] or '—'}")
                    st.write(f"**Mental state:** {session['mental_state'] or '—'}")
                    st.write(f"**Techniques:** {session['techniques'] or '—'}")
                    st.write(f"**Brushes:** {session['brushes_used'] or '—'}")
                with col2:
                    st.write(f"**Completion:** {session['completion_percent'] or 0}%")
                    st.write(f"**What I worked on:** {session['what_worked_on'] or '—'}")
                    st.write(f"**What worked:** {session['what_worked'] or '—'}")
                    st.write(f"**What didn't work:** {session['what_didnt_work'] or '—'}")
                    st.write(f"**Do differently:** {session['do_differently'] or '—'}")
                    st.write(f"**Notes:** {session['notes'] or '—'}")
                if session["image_path"]:
                    st.image(session["image_path"], caption="Session photo", width=300)

conn.close()