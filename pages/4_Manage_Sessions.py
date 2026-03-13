import streamlit as st
from database import get_connection
from config import (
    LOCATIONS, LIGHTING, REFERENCE_TYPES,
    TECHNIQUES, MENTAL_STATES, BRUSH_SIZES
)
import os
from datetime import date, datetime

st.set_page_config(page_title="Manage Sessions", page_icon="🎨")
st.title("🎨 Manage Sessions")

st.markdown("""
Log a painting session each time you sit down to work. Record how long you painted, what you worked on, which colors and techniques you used, and how the session felt. The more consistently you log, the more your dashboard will reveal about your creative process.
""")

conn = get_connection()

paintings = conn.execute(
    "SELECT id, title FROM paintings ORDER BY title"
).fetchall()

if not paintings:
    st.warning("No paintings yet. Please add a painting first.")
    st.stop()

painting_options = {row["title"]: row["id"] for row in paintings}

tab1, tab2 = st.tabs(["Add New Session", "Edit / Delete Sessions"])

with tab1:
    my_paints = conn.execute("SELECT * FROM paints ORDER BY brand, name").fetchall()

    st.subheader("Colors used in this session")
    if not my_paints:
        st.info("Your palette is empty. Add paints in the My Palette page first.")
        selected_colors = []
    else:
        selected_colors = []
        cols = st.columns(8)
        for i, paint in enumerate(my_paints):
            with cols[i % 8]:
                key = f"color_{paint['id']}"
                checked = st.checkbox(" ", key=key, help=paint["name"])
                st.markdown(
                    f'<div style="background-color:{paint["hex_color"]};width:36px;height:36px;border-radius:4px;border:{"3px solid #333" if checked else "1px solid #ccc"}"></div>',
                    unsafe_allow_html=True
                )
                st.caption(paint["name"].split(" ")[-1])
                if checked:
                    selected_colors.append(paint["name"])

    st.markdown("---")

    with st.form("session_form"):
        painting_title = st.selectbox("Painting *", list(painting_options.keys()))
        col1, col2 = st.columns(2)
        with col1:
            session_date = st.date_input("Date *", value=date.today())
            start_time = st.time_input("Start time")
            end_time = st.time_input("End time")
            location = st.selectbox("Location", [""] + LOCATIONS)
            lighting = st.selectbox("Lighting", [""] + LIGHTING)
            mental_state = st.selectbox("Mental / physical state", [""] + MENTAL_STATES)
            rating = st.slider("Session rating *", 1, 5, 3)
        with col2:
            completion_percent = st.slider("Estimated completion %", 0, 100, 0)
            reference_used = st.selectbox("Reference used", [""] + REFERENCE_TYPES)
            reference_detail = st.text_input("Reference detail")
            techniques = st.multiselect("Techniques used", TECHNIQUES)
            brushes = st.multiselect("Brushes used", BRUSH_SIZES)

        what_worked_on = st.text_area("What I worked on")
        whats_next = st.text_area("What's next")
        what_worked = st.text_area("What worked")
        what_didnt = st.text_area("What did not work")
        do_differently = st.text_area("What I would do differently")
        notes = st.text_area("Free notes")
        image_file = st.file_uploader("Session photo", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Save Session")

        if submitted:
            painting_id = painting_options[painting_title]
            start_dt = datetime.combine(date.today(), start_time)
            end_dt = datetime.combine(date.today(), end_time)
            duration = max(0, int((end_dt - start_dt).total_seconds() / 60))

            image_path = None
            if image_file:
                images_dir = os.path.join(os.path.dirname(__file__), "..", "images")
                os.makedirs(images_dir, exist_ok=True)
                image_path = os.path.join(images_dir, f"{painting_id}_{session_date}_{image_file.name}")
                with open(image_path, "wb") as f:
                    f.write(image_file.getbuffer())

            session_count = conn.execute(
                "SELECT COUNT(*) as count FROM sessions WHERE painting_id = ?",
                (painting_id,)
            ).fetchone()["count"]

            conn.execute("""
                INSERT INTO sessions (
                    painting_id, date, start_time, end_time, duration_minutes,
                    completion_percent, location, lighting, reference_used,
                    reference_detail, what_worked_on, whats_next, techniques,
                    colors_used, brushes_used, mental_state, what_worked,
                    what_didnt_work, do_differently, rating, notes, image_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                painting_id, str(session_date),
                str(start_time), str(end_time), duration,
                completion_percent, location, lighting,
                reference_used, reference_detail,
                what_worked_on, whats_next,
                ", ".join(techniques),
                ", ".join(selected_colors),
                ", ".join(brushes), mental_state,
                what_worked, what_didnt, do_differently,
                rating, notes, image_path
            ))
            conn.commit()

            st.success("Session saved successfully!")

            avg_rating = conn.execute(
                "SELECT AVG(rating) as avg FROM sessions WHERE painting_id = ?",
                (painting_id,)
            ).fetchone()["avg"]

            st.info(f"""
                **Session summary**
                - Duration: {duration} minutes
                - Session number: {session_count + 1} for this painting
                - Completion: {completion_percent}%
                - Your rating: {rating}/5
                - Average rating for this painting: {avg_rating:.1f}/5
                - Colors used: {", ".join(selected_colors) if selected_colors else "none selected"}
            """)

with tab2:
    st.subheader("All sessions")
    sessions = conn.execute("""
        SELECT s.*, p.title as painting_title
        FROM sessions s
        JOIN paintings p ON s.painting_id = p.id
        ORDER BY s.date DESC
    """).fetchall()

    if not sessions:
        st.info("No sessions yet. Add one in the first tab.")
    else:
        for session in sessions:
            with st.expander(f"🎨 {session['painting_title']} — {session['date']} — Rating {session['rating'] or '—'}/5"):
                if st.button("Edit this session", key=f"edit_session_{session['id']}"):
                    st.session_state[f"editing_session_{session['id']}"] = True

                if st.session_state.get(f"editing_session_{session['id']}"):
                    with st.form(f"edit_session_form_{session['id']}"):
                        edit_painting = st.selectbox(
                            "Painting *",
                            list(painting_options.keys()),
                            index=list(painting_options.values()).index(session["painting_id"]) if session["painting_id"] in painting_options.values() else 0
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_date = st.text_input("Date", value=session["date"] or "")
                            edit_start = st.text_input("Start time", value=session["start_time"] or "")
                            edit_end = st.text_input("End time", value=session["end_time"] or "")
                            edit_location = st.selectbox("Location", [""] + LOCATIONS,
                                index=([""] + LOCATIONS).index(session["location"]) if session["location"] in LOCATIONS else 0)
                            edit_lighting = st.selectbox("Lighting", [""] + LIGHTING,
                                index=([""] + LIGHTING).index(session["lighting"]) if session["lighting"] in LIGHTING else 0)
                            edit_mental = st.selectbox("Mental state", [""] + MENTAL_STATES,
                                index=([""] + MENTAL_STATES).index(session["mental_state"]) if session["mental_state"] in MENTAL_STATES else 0)
                            edit_rating = st.slider("Rating", 1, 5, int(session["rating"] or 3))
                        with col2:
                            edit_completion = st.slider("Completion %", 0, 100, int(session["completion_percent"] or 0))
                            edit_reference = st.selectbox("Reference used", [""] + REFERENCE_TYPES,
                                index=([""] + REFERENCE_TYPES).index(session["reference_used"]) if session["reference_used"] in REFERENCE_TYPES else 0)
                            edit_reference_detail = st.text_input("Reference detail", value=session["reference_detail"] or "")
                            edit_techniques = st.multiselect("Techniques", TECHNIQUES,
                                default=[t for t in (session["techniques"] or "").split(", ") if t in TECHNIQUES])
                            edit_brushes = st.multiselect("Brushes", BRUSH_SIZES,
                                default=[b for b in (session["brushes_used"] or "").split(", ") if b in BRUSH_SIZES])
                        edit_worked_on = st.text_area("What I worked on", value=session["what_worked_on"] or "")
                        edit_whats_next = st.text_area("What's next", value=session["whats_next"] or "")
                        edit_what_worked = st.text_area("What worked", value=session["what_worked"] or "")
                        edit_what_didnt = st.text_area("What did not work", value=session["what_didnt_work"] or "")
                        edit_differently = st.text_area("Do differently", value=session["do_differently"] or "")
                        edit_notes = st.text_area("Notes", value=session["notes"] or "")
                        save_edit = st.form_submit_button("Save changes")
                        if save_edit:
                            conn.execute("""
                                UPDATE sessions SET
                                    painting_id=?, date=?, start_time=?, end_time=?,
                                    location=?, lighting=?, mental_state=?, rating=?,
                                    completion_percent=?, reference_used=?, reference_detail=?,
                                    techniques=?, brushes_used=?, what_worked_on=?, whats_next=?,
                                    what_worked=?, what_didnt_work=?, do_differently=?, notes=?
                                WHERE id=?
                            """, (
                                painting_options[edit_painting], edit_date, edit_start, edit_end,
                                edit_location, edit_lighting, edit_mental, edit_rating,
                                edit_completion, edit_reference, edit_reference_detail,
                                ", ".join(edit_techniques), ", ".join(edit_brushes),
                                edit_worked_on, edit_whats_next, edit_what_worked,
                                edit_what_didnt, edit_differently, edit_notes,
                                session["id"]
                            ))
                            conn.commit()
                            st.session_state[f"editing_session_{session['id']}"] = False
                            st.success("Session updated successfully!")
                            st.rerun()

                st.markdown("---")
                if st.button("Delete this session", key=f"delete_session_{session['id']}"):
                    st.session_state[f"confirm_delete_session_{session['id']}"] = True

                if st.session_state.get(f"confirm_delete_session_{session['id']}"):
                    st.error(f"Are you sure you want to delete this session? This cannot be undone.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Yes, delete", key=f"yes_delete_session_{session['id']}"):
                            conn.execute("DELETE FROM sessions WHERE id = ?", (session["id"],))
                            conn.commit()
                            st.session_state[f"confirm_delete_session_{session['id']}"] = False
                            st.success("Session deleted.")
                            st.rerun()
                    with col2:
                        if st.button("Cancel", key=f"cancel_delete_session_{session['id']}"):
                            st.session_state[f"confirm_delete_session_{session['id']}"] = False
                            st.rerun()

conn.close()