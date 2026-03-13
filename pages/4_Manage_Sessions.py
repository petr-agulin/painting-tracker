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

conn.close()