import streamlit as st
from database import get_connection

st.set_page_config(page_title="Browse Paintings and Sessions", page_icon="🔍")
st.title("🔍 Browse Paintings & Sessions")

conn = get_connection()

tab1, tab2 = st.tabs(["Paintings", "Sessions"])

with tab1:
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Filter by status", ["All", "In progress", "Complete", "Abandoned", "Not started"])
    with col2:
        genres = ["All"] + [
            row["genre"] for row in conn.execute(
                "SELECT DISTINCT genre FROM paintings WHERE genre != '' AND genre IS NOT NULL"
            ).fetchall()
        ]
        genre_filter = st.selectbox("Filter by genre", genres)
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
    query += " ORDER BY title"

    paintings = conn.execute(query, params).fetchall()

    if not paintings:
        st.info("No paintings found.")
    else:
        st.markdown(f"**{len(paintings)} painting(s) found**")
        for painting in paintings:
            sessions = conn.execute(
                "SELECT * FROM sessions WHERE painting_id = ? ORDER BY date ASC",
                (painting["id"],)
            ).fetchall()
            total_minutes = sum(s["duration_minutes"] or 0 for s in sessions)
            latest_completion = sessions[-1]["completion_percent"] if sessions else 0

            with st.expander(f"🖼️ {painting['title']} — {painting['status']} — {len(sessions)} session(s)"):
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
                    st.write(f"**Total time:** {total_minutes // 60}h {total_minutes % 60}m")
                    st.write(f"**Completion:** {latest_completion or 0}%")

                if sessions:
                    st.markdown("---")
                    st.markdown("**Session timeline**")
                    for i, session in enumerate(sessions):
                        with st.expander(f"Session {i+1} — {session['date']} — Rating {session['rating'] or '—'}/5", expanded=False):
                            col1, col2 = st.columns([2, 3])
                            with col1:
                                if session["image_path"]:
                                    st.image(session["image_path"], caption=f"Session {i+1}", use_column_width=True)
                                else:
                                    st.markdown(
                                        '<div style="background:#f0f0f0;height:120px;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#aaa">No photo</div>',
                                        unsafe_allow_html=True
                                    )
                            with col2:
                                st.write(f"**Duration:** {session['duration_minutes'] or 0} min")
                                st.write(f"**Completion:** {session['completion_percent'] or 0}%")
                                st.write(f"**Mental state:** {session['mental_state'] or '—'}")
                                st.write(f"**Techniques:** {session['techniques'] or '—'}")
                                st.write(f"**Colors used:** {session['colors_used'] or '—'}")
                                st.write(f"**Brushes:** {session['brushes_used'] or '—'}")
                                if session["what_worked_on"]:
                                    st.write(f"**Worked on:** {session['what_worked_on']}")
                                if session["what_worked"]:
                                    st.write(f"**What worked:** {session['what_worked']}")
                                if session["what_didnt_work"]:
                                    st.write(f"**What did not work:** {session['what_didnt_work']}")
                                if session["do_differently"]:
                                    st.write(f"**Do differently:** {session['do_differently']}")
                                if session["notes"]:
                                    st.write(f"**Notes:** {session['notes']}")
                            if session["completion_percent"]:
                                st.progress(session["completion_percent"] / 100)

with tab2:
    col1, col2, col3 = st.columns(3)
    with col1:
        rating_filter = st.selectbox("Filter by rating", ["All", "5", "4", "3", "2", "1"])
    with col2:
        states = ["All"] + [
            row["mental_state"] for row in conn.execute(
                "SELECT DISTINCT mental_state FROM sessions WHERE mental_state != '' AND mental_state IS NOT NULL"
            ).fetchall()
        ]
        state_filter = st.selectbox("Filter by mental state", states)
    with col3:
        painting_filter_options = ["All"] + [
            row["title"] for row in conn.execute("SELECT title FROM paintings ORDER BY title").fetchall()
        ]
        painting_filter = st.selectbox("Filter by painting", painting_filter_options)

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
    if painting_filter != "All":
        query += " AND p.title = ?"
        params.append(painting_filter)
    query += " ORDER BY s.date DESC"

    sessions = conn.execute(query, params).fetchall()

    if not sessions:
        st.info("No sessions found.")
    else:
        st.markdown(f"**{len(sessions)} session(s) found**")
        for session in sessions:
            with st.expander(f"🎨 {session['painting_title']} — {session['date']} — Rating {session['rating'] or '—'}/5", expanded=False):
                st.markdown(f"**Painting:** {session['painting_title']}")
                col1, col2 = st.columns([2, 3])
                with col1:
                    if session["image_path"]:
                        st.image(session["image_path"], caption="Session photo", use_column_width=True)
                    else:
                        st.markdown(
                            '<div style="background:#f0f0f0;height:120px;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#aaa">No photo</div>',
                            unsafe_allow_html=True
                        )
                with col2:
                    st.write(f"**Date:** {session['date']}")
                    st.write(f"**Duration:** {session['duration_minutes'] or 0} min")
                    st.write(f"**Completion:** {session['completion_percent'] or 0}%")
                    st.write(f"**Rating:** {session['rating'] or '—'}/5")
                    st.write(f"**Mental state:** {session['mental_state'] or '—'}")
                    st.write(f"**Location:** {session['location'] or '—'}")
                    st.write(f"**Lighting:** {session['lighting'] or '—'}")
                    st.write(f"**Techniques:** {session['techniques'] or '—'}")
                    st.write(f"**Colors used:** {session['colors_used'] or '—'}")
                    st.write(f"**Brushes:** {session['brushes_used'] or '—'}")
                    if session["what_worked_on"]:
                        st.write(f"**Worked on:** {session['what_worked_on']}")
                    if session["what_worked"]:
                        st.write(f"**What worked:** {session['what_worked']}")
                    if session["what_didnt_work"]:
                        st.write(f"**What did not work:** {session['what_didnt_work']}")
                    if session["do_differently"]:
                        st.write(f"**Do differently:** {session['do_differently']}")
                    if session["notes"]:
                        st.write(f"**Notes:** {session['notes']}")

conn.close()