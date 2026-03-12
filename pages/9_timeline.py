import streamlit as st
from database import get_connection

st.set_page_config(page_title="Progress Timeline", page_icon="📈")
st.title("📈 Painting Progress Timeline")

conn = get_connection()

paintings = conn.execute(
    "SELECT id, title FROM paintings ORDER BY title"
).fetchall()

if not paintings:
    st.info("No paintings yet. Add a painting first.")
    st.stop()

painting_options = {row["title"]: row["id"] for row in paintings}
selected_title = st.selectbox("Select a painting", list(painting_options.keys()))

if selected_title:
    painting_id = painting_options[selected_title]
    sessions = conn.execute(
        "SELECT * FROM sessions WHERE painting_id = ? ORDER BY date ASC",
        (painting_id,)
    ).fetchall()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total sessions", len(sessions))
    with col2:
        total_minutes = sum(s["duration_minutes"] or 0 for s in sessions)
        st.metric("Total time", f"{total_minutes // 60}h {total_minutes % 60}m")
    with col3:
        if sessions:
            latest_completion = sessions[-1]["completion_percent"] or 0
            st.metric("Current completion", f"{latest_completion}%")
            st.progress(latest_completion / 100)

    st.markdown("---")

    if not sessions:
        st.info("No sessions logged for this painting yet.")
    else:
        for i, session in enumerate(sessions):
            st.markdown(f"### Session {i + 1} — {session['date']}")
            col1, col2 = st.columns([2, 3])
            with col1:
                if session["image_path"]:
                    st.image(session["image_path"], caption=f"After session {i + 1}", use_column_width=True)
                else:
                    st.markdown(
                        '<div style="background:#f0f0f0;height:150px;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#aaa">No photo</div>',
                        unsafe_allow_html=True
                    )
            with col2:
                st.write(f"**Duration:** {session['duration_minutes'] or 0} minutes")
                st.write(f"**Completion after session:** {session['completion_percent'] or 0}%")
                st.write(f"**Rating:** {session['rating'] or 0}/5")
                st.write(f"**Mental state:** {session['mental_state'] or 'not noted'}")
                st.write(f"**Techniques:** {session['techniques'] or 'not noted'}")
                st.write(f"**Colors used:** {session['colors_used'] or 'not noted'}")
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
                st.progress(
                    session["completion_percent"] / 100,
                    text=f"{session['completion_percent']}% complete after session {i + 1}"
                )
            st.markdown("---")

conn.close()