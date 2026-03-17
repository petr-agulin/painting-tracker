import streamlit as st
from database import get_connection
from config import (
    PAPER_SIZES, GENRES,
    INSPIRATION_CATEGORIES, STATUS_OPTIONS,
    LOCATIONS, LIGHTING, REFERENCE_TYPES,
    TECHNIQUES, MENTAL_STATES, BRUSH_SIZES
)
import os
import base64
from datetime import date, datetime

MOODS = ["Calm", "Cozy", "Dark", "Dramatic", "Dreamy", "Dynamic", "Ethereal", "Intimate", "Melancholic", "Mysterious", "Nostalgic", "Playful", "Romantic", "Surreal", "Whimsical"]

PAPER_TYPES = [
    "Cotton Cold Press",
    "Cotton Hot Press",
    "Cotton Rough",
    "Cellulose Cold Press",
    "Cellulose Hot Press",
    "Cellulose Rough",
    "Cotton / Cellulose Blend Cold Press",
    "Cotton / Cellulose Blend Hot Press",
    "Cotton / Cellulose Blend Rough"
]

STYLES = [
    "Realistic",
    "Semi-realistic",
    "Impressionistic",
    "Expressionistic",
    "Loose / Gestural",
    "Painterly",
    "Plein Air",
    "Illustrative",
    "Botanical",
    "Sketch",
    "Minimal",
    "Abstract",
    "Semi-abstract",
    "Naive",
    "Other"
]

def image_link(image_path, label="View full size"):
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = image_path.split(".")[-1].lower()
    mime = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
    href = f'<a href="data:{mime};base64,{data}" target="_blank">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)

@st.dialog("Add New Session", width="large")
def add_session_dialog(painting_id, painting_title, IMAGES_DIR):
    conn = get_connection()
    st.markdown(f"**Painting:** {painting_title}")

    with st.form("dialog_session_form"):
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
            colors_used = st.text_input("Colors used", placeholder="e.g. Ultramarine, Burnt Sienna")

        what_worked_on = st.text_area("What I worked on")
        whats_next = st.text_area("What's next")
        what_worked = st.text_area("What worked")
        what_didnt = st.text_area("What did not work")
        do_differently = st.text_area("What I would do differently")
        notes = st.text_area("Free notes")
        image_file = st.file_uploader("Session photo", type=["jpg", "jpeg", "png"])

        col1, col2 = st.columns(2)
        with col1:
            save_session = st.form_submit_button("Save Session")
        with col2:
            cancel_session = st.form_submit_button("Cancel")

        if cancel_session:
            st.rerun()

        if save_session:
            start_dt = datetime.combine(date.today(), start_time)
            end_dt = datetime.combine(date.today(), end_time)
            duration = max(0, int((end_dt - start_dt).total_seconds() / 60))

            image_path = None
            if image_file:
                image_path = os.path.join(IMAGES_DIR, f"{painting_id}_{session_date}_{image_file.name}")
                with open(image_path, "wb") as f:
                    f.write(image_file.getbuffer())

            session_count_now = conn.execute(
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
                colors_used,
                ", ".join(brushes), mental_state,
                what_worked, what_didnt, do_differently,
                rating, notes, image_path
            ))
            conn.commit()
            st.success(f"Session saved! Duration: {duration} minutes. Session {session_count_now + 1} for this painting.")
            st.rerun()

@st.dialog("Edit Session", width="large")
def edit_session_dialog(session_id, IMAGES_DIR):
    conn = get_connection()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not session:
        st.error("Session not found.")
        return

    painting = conn.execute("SELECT title FROM paintings WHERE id = ?", (session["painting_id"],)).fetchone()
    st.markdown(f"**Painting:** {painting['title'] if painting else '—'}")

    with st.form("edit_session_dialog_form"):
        col1, col2 = st.columns(2)
        with col1:
            session_date = st.text_input("Date *", value=session["date"] or "")
            start_time = st.text_input("Start time", value=session["start_time"] or "")
            end_time = st.text_input("End time", value=session["end_time"] or "")
            location = st.selectbox("Location", [""] + LOCATIONS,
                index=([""] + LOCATIONS).index(session["location"]) if session["location"] in LOCATIONS else 0)
            lighting = st.selectbox("Lighting", [""] + LIGHTING,
                index=([""] + LIGHTING).index(session["lighting"]) if session["lighting"] in LIGHTING else 0)
            mental_state = st.selectbox("Mental / physical state", [""] + MENTAL_STATES,
                index=([""] + MENTAL_STATES).index(session["mental_state"]) if session["mental_state"] in MENTAL_STATES else 0)
            rating = st.slider("Session rating *", 1, 5, int(session["rating"] or 3))
        with col2:
            completion_percent = st.slider("Estimated completion %", 0, 100, int(session["completion_percent"] or 0))
            reference_used = st.selectbox("Reference used", [""] + REFERENCE_TYPES,
                index=([""] + REFERENCE_TYPES).index(session["reference_used"]) if session["reference_used"] in REFERENCE_TYPES else 0)
            reference_detail = st.text_input("Reference detail", value=session["reference_detail"] or "")
            techniques = st.multiselect("Techniques used", TECHNIQUES,
                default=[t for t in (session["techniques"] or "").split(", ") if t in TECHNIQUES])
            brushes = st.multiselect("Brushes used", BRUSH_SIZES,
                default=[b for b in (session["brushes_used"] or "").split(", ") if b in BRUSH_SIZES])
            colors_used = st.text_input("Colors used", value=session["colors_used"] or "",
                placeholder="e.g. Ultramarine, Burnt Sienna")

        what_worked_on = st.text_area("What I worked on", value=session["what_worked_on"] or "")
        whats_next = st.text_area("What's next", value=session["whats_next"] or "")
        what_worked = st.text_area("What worked", value=session["what_worked"] or "")
        what_didnt = st.text_area("What did not work", value=session["what_didnt_work"] or "")
        do_differently = st.text_area("What I would do differently", value=session["do_differently"] or "")
        notes = st.text_area("Free notes", value=session["notes"] or "")

        if session["image_path"] and os.path.exists(session["image_path"]):
            st.image(session["image_path"], width=150)
            remove_image = st.checkbox("Remove current photo")
        else:
            remove_image = False

        new_image = st.file_uploader("Upload new session photo", type=["jpg", "jpeg", "png"])

        col1, col2 = st.columns(2)
        with col1:
            save = st.form_submit_button("Save changes")
        with col2:
            cancel = st.form_submit_button("Cancel")

        if cancel:
            st.rerun()

        if save:
            new_image_path = session["image_path"]
            if remove_image:
                if session["image_path"] and os.path.exists(session["image_path"]):
                    os.remove(session["image_path"])
                new_image_path = None
            if new_image:
                if session["image_path"] and os.path.exists(session["image_path"]):
                    os.remove(session["image_path"])
                new_image_path = os.path.join(IMAGES_DIR, f"{session['painting_id']}_{session_date}_{new_image.name}")
                with open(new_image_path, "wb") as f:
                    f.write(new_image.getbuffer())

            try:
                start_dt = datetime.strptime(start_time, "%H:%M:%S")
                end_dt = datetime.strptime(end_time, "%H:%M:%S")
                duration = max(0, int((end_dt - start_dt).total_seconds() / 60))
            except Exception:
                duration = session["duration_minutes"] or 0

            conn.execute("""
                UPDATE sessions SET
                    date=?, start_time=?, end_time=?, duration_minutes=?,
                    completion_percent=?, location=?, lighting=?, reference_used=?,
                    reference_detail=?, what_worked_on=?, whats_next=?, techniques=?,
                    colors_used=?, brushes_used=?, mental_state=?, what_worked=?,
                    what_didnt_work=?, do_differently=?, rating=?, notes=?, image_path=?
                WHERE id=?
            """, (
                session_date, start_time, end_time, duration,
                completion_percent, location, lighting, reference_used,
                reference_detail, what_worked_on, whats_next,
                ", ".join(techniques), colors_used,
                ", ".join(brushes), mental_state, what_worked,
                what_didnt, do_differently, rating, notes, new_image_path,
                session_id
            ))
            conn.commit()
            st.success("Session updated!")
            st.rerun()

st.set_page_config(page_title="Manage Paintings", page_icon="🖼️")
st.title("🖼️ Manage Paintings")

st.markdown("""
Add new paintings and manage existing ones. A painting is the starting point — log sessions against it each time you sit down to work on it. Fill in as much or as little as you like; only the title is required.
""")

conn = get_connection()

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

if "paintings_page_loaded" not in st.session_state:
    st.session_state["paintings_page_loaded"] = True
    for key in list(st.session_state.keys()):
        if key.startswith("editing_") or key.startswith("confirm_delete_"):
            st.session_state[key] = False

tab1, tab2 = st.tabs(["Paintings", "Add new"])

with tab1:
    paintings_all = conn.execute("SELECT * FROM paintings ORDER BY title").fetchall()

    if not paintings_all:
        st.info("No paintings yet. Add one in the Add new tab.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            status_filter = st.selectbox("Filter by status", ["All"] + STATUS_OPTIONS, key="manage_status_filter")
        with col2:
            available_genres = ["All"] + [
                row["genre"] for row in conn.execute(
                    "SELECT DISTINCT genre FROM paintings WHERE genre != '' AND genre IS NOT NULL"
                ).fetchall()
            ]
            genre_filter = st.selectbox("Filter by genre", available_genres, key="manage_genre_filter")
        with col3:
            available_series = ["All"] + [
                row["name"] for row in conn.execute(
                    "SELECT name FROM series ORDER BY name"
                ).fetchall()
            ]
            series_filter = st.selectbox("Filter by series", available_series, key="manage_series_filter")
        with col4:
            search = st.text_input("Search by title", key="manage_search")

        paintings = [p for p in paintings_all if
            (status_filter == "All" or p["status"] == status_filter) and
            (genre_filter == "All" or p["genre"] == genre_filter) and
            (series_filter == "All" or conn.execute(
                "SELECT name FROM series WHERE id = ?", (p["series_id"],)
            ).fetchone() and conn.execute(
                "SELECT name FROM series WHERE id = ?", (p["series_id"],)
            ).fetchone()["name"] == series_filter) and
            (not search or search.lower() in p["title"].lower())
        ]

        st.markdown(f"**{len(paintings)} painting(s) found**")

        for painting in paintings:
            session_count = conn.execute(
                "SELECT COUNT(*) as c FROM sessions WHERE painting_id = ?",
                (painting["id"],)
            ).fetchone()["c"]

            editing = st.session_state.get(f"editing_{painting['id']}", False)

            with st.expander(f"🖼️ {painting['title']} — {painting['status']}"):
                if not editing:
                    series_name_display = "—"
                    if painting["series_id"]:
                        series_row = conn.execute(
                            "SELECT name FROM series WHERE id = ?", (painting["series_id"],)
                        ).fetchone()
                        if series_row:
                            series_name_display = series_row["name"]

                    total_minutes = conn.execute(
                        "SELECT SUM(duration_minutes) as t FROM sessions WHERE painting_id = ?",
                        (painting["id"],)
                    ).fetchone()["t"] or 0

                    latest_completion = conn.execute(
                        "SELECT completion_percent FROM sessions WHERE painting_id = ? ORDER BY date DESC LIMIT 1",
                        (painting["id"],)
                    ).fetchone()
                    completion = latest_completion["completion_percent"] if latest_completion else 0

                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Series:** {series_name_display}")
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
                        st.write(f"**Sessions:** {session_count}")
                        st.write(f"**Total time:** {total_minutes // 60}h {total_minutes % 60}m")
                        st.write(f"**Completion:** {completion or 0}%")

                    if painting["image_path"] and os.path.exists(painting["image_path"]):
                        st.image(painting["image_path"], width=150)
                        image_link(painting["image_path"], "View full size")
                    else:
                        st.caption("No preview photo.")

                    st.markdown("---")
                    if st.button("Edit this painting", key=f"edit_{painting['id']}"):
                        st.session_state[f"editing_{painting['id']}"] = True
                        st.rerun()

                    if st.button("Delete this painting", key=f"delete_{painting['id']}"):
                        st.session_state[f"confirm_delete_{painting['id']}"] = True

                    if session_count > 0:
                        st.warning(f"Deleting will also remove {session_count} linked session(s).")

                    if st.session_state.get(f"confirm_delete_{painting['id']}"):
                        st.error(f"Are you sure you want to delete '{painting['title']}'? This cannot be undone.")
                        if st.button("Yes, delete", key=f"yes_delete_{painting['id']}"):
                            if painting["image_path"] and os.path.exists(painting["image_path"]):
                                os.remove(painting["image_path"])
                            conn.execute("DELETE FROM sessions WHERE painting_id = ?", (painting["id"],))
                            conn.execute("DELETE FROM paintings WHERE id = ?", (painting["id"],))
                            conn.commit()
                            st.session_state[f"confirm_delete_{painting['id']}"] = False
                            st.success("Painting deleted.")
                            st.rerun()
                        if st.button("Cancel", key=f"cancel_delete_{painting['id']}"):
                            st.session_state[f"confirm_delete_{painting['id']}"] = False
                            st.rerun()

                    sessions_for_painting = conn.execute(
                        "SELECT * FROM sessions WHERE painting_id = ? ORDER BY date DESC",
                        (painting["id"],)
                    ).fetchall()

                    st.markdown("---")
                    st.markdown("**Session timeline**")

                    if st.button("+ Add new session", key=f"add_session_btn_{painting['id']}"):
                        add_session_dialog(painting["id"], painting["title"], IMAGES_DIR)

                    if sessions_for_painting:
                        total_sessions = len(sessions_for_painting)
                        for i, session in enumerate(sessions_for_painting):
                            session_num = total_sessions - i
                            with st.expander(f"Session {session_num} — {session['date']} — Rating {session['rating'] or '—'}/5", expanded=False):
                                col1, col2 = st.columns([2, 3])
                                with col1:
                                    if session["image_path"]:
                                        st.image(session["image_path"], caption=f"Session {session_num}", use_container_width=True)
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
                                    st.progress(session["completion_percent"] / 100, text=f"{session['completion_percent']}%")

                                st.markdown("---")
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("Edit session", key=f"edit_session_{session['id']}"):
                                        edit_session_dialog(session["id"], IMAGES_DIR)
                                with col2:
                                    if st.button("Delete session", key=f"delete_session_{session['id']}"):
                                        st.session_state[f"confirm_delete_session_{session['id']}"] = True

                                if st.session_state.get(f"confirm_delete_session_{session['id']}"):
                                    st.error("Are you sure you want to delete this session? This cannot be undone.")
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("Yes, delete", key=f"yes_delete_session_{session['id']}"):
                                            if session["image_path"] and os.path.exists(session["image_path"]):
                                                os.remove(session["image_path"])
                                            conn.execute("DELETE FROM sessions WHERE id = ?", (session["id"],))
                                            conn.commit()
                                            st.session_state[f"confirm_delete_session_{session['id']}"] = False
                                            st.rerun()
                                    with col2:
                                        if st.button("Cancel", key=f"cancel_delete_session_{session['id']}"):
                                            st.session_state[f"confirm_delete_session_{session['id']}"] = False
                                            st.rerun()

                else:
                    series_rows = conn.execute("SELECT id, name FROM series").fetchall()
                    series_options_edit = {"-- No series --": None}
                    series_options_edit.update({row["name"]: row["id"] for row in series_rows})
                    current_series = next(
                        (name for name, sid in series_options_edit.items() if sid == painting["series_id"]),
                        "-- No series --"
                    )

                    edit_status_key = f"edit_status_{painting['id']}"
                    if edit_status_key not in st.session_state:
                        st.session_state[edit_status_key] = painting["status"] if painting["status"] in STATUS_OPTIONS else STATUS_OPTIONS[0]

                    new_status = st.selectbox(
                        "Status",
                        STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(st.session_state[edit_status_key]),
                        key=edit_status_key
                    )

                    with st.form(f"edit_form_{painting['id']}"):
                        new_title = st.text_input("Title *", value=painting["title"])
                        new_series = st.selectbox("Series", list(series_options_edit.keys()),
                            index=list(series_options_edit.keys()).index(current_series))
                        new_genre = st.selectbox("Genre", [""] + GENRES,
                            index=([""] + GENRES).index(painting["genre"]) if painting["genre"] in GENRES else 0)
                        new_subject = st.text_input("Subject", value=painting["subject"] or "")
                        new_style = st.multiselect("Style", STYLES,
                            default=[s for s in (painting["style"] or "").split(", ") if s in STYLES])
                        new_mood = st.multiselect("Mood", MOODS,
                            default=[m for m in (painting["mood"] or "").split(", ") if m in MOODS])
                        col1, col2 = st.columns(2)
                        with col1:
                            new_size = st.selectbox("Paper size", [""] + PAPER_SIZES,
                                index=([""] + PAPER_SIZES).index(painting["paper_size"]) if painting["paper_size"] in PAPER_SIZES else 0)
                        with col2:
                            new_type = st.selectbox("Paper type", [""] + PAPER_TYPES,
                                index=([""] + PAPER_TYPES).index(painting["paper_type"]) if painting["paper_type"] in PAPER_TYPES else 0)

                        new_date_started = None
                        new_date_finished = None
                        if new_status != "Not started":
                            new_date_started = st.text_input("Date started", value=painting["date_started"] or "")
                        if new_status == "Complete":
                            new_date_finished = st.text_input("Date finished", value=painting["date_finished"] or "")

                        new_inspiration_cat = st.selectbox("Inspiration source", [""] + INSPIRATION_CATEGORIES,
                            index=([""] + INSPIRATION_CATEGORIES).index(painting["inspiration_category"]) if painting["inspiration_category"] in INSPIRATION_CATEGORIES else 0)
                        new_inspiration_note = st.text_area("Inspiration note", value=painting["inspiration_note"] or "")

                        if painting["image_path"] and os.path.exists(painting["image_path"]):
                            st.image(painting["image_path"], width=150)
                            image_link(painting["image_path"], "View full size")
                            remove_image = st.checkbox("Remove current photo")
                        else:
                            remove_image = False

                        new_image = st.file_uploader("Upload new preview photo", type=["jpg", "jpeg", "png"], key=f"img_{painting['id']}")

                        col1, col2 = st.columns(2)
                        with col1:
                            save_edit = st.form_submit_button("Save changes")
                        with col2:
                            cancel_edit = st.form_submit_button("Cancel")

                        if cancel_edit:
                            st.session_state[f"editing_{painting['id']}"] = False
                            st.rerun()

                        if save_edit:
                            if not new_title:
                                st.error("Title cannot be empty.")
                            else:
                                new_image_path = painting["image_path"]

                                if remove_image:
                                    if painting["image_path"] and os.path.exists(painting["image_path"]):
                                        os.remove(painting["image_path"])
                                    new_image_path = None

                                if new_image:
                                    if painting["image_path"] and os.path.exists(painting["image_path"]):
                                        os.remove(painting["image_path"])
                                    new_image_path = os.path.join(IMAGES_DIR, f"painting_preview_{new_title}_{new_image.name}")
                                    with open(new_image_path, "wb") as f:
                                        f.write(new_image.getbuffer())

                                conn.execute("""
                                    UPDATE paintings SET
                                        title=?, status=?, date_started=?, date_finished=?,
                                        paper_size=?, paper_type=?, genre=?, subject=?,
                                        style=?, mood=?, series_id=?,
                                        inspiration_category=?, inspiration_note=?,
                                        image_path=?
                                    WHERE id=?
                                """, (
                                    new_title, new_status,
                                    new_date_started, new_date_finished,
                                    new_size, new_type, new_genre, new_subject,
                                    ", ".join(new_style), ", ".join(new_mood),
                                    series_options_edit.get(new_series),
                                    new_inspiration_cat, new_inspiration_note,
                                    new_image_path, painting["id"]
                                ))
                                conn.commit()
                                st.session_state[f"editing_{painting['id']}"] = False
                                st.success("Painting updated successfully!")
                                st.rerun()

with tab2:
    series_rows = conn.execute("SELECT id, name FROM series").fetchall()
    series_options = {"-- No series --": None}
    series_options.update({row["name"]: row["id"] for row in series_rows})

    status = st.selectbox("Status *", STATUS_OPTIONS, key="new_status")

    with st.form("new_painting_form"):
        title = st.text_input("Painting title *", placeholder="e.g. Morning Light on the Canal")
        series_name = st.selectbox("Series", list(series_options.keys()))
        genre = st.selectbox("Genre", [""] + GENRES)
        subject = st.text_input("Subject", placeholder="e.g. Canal in Amsterdam at dawn")
        style = st.multiselect("Style", STYLES)
        mood = st.multiselect("Mood", MOODS)
        col1, col2 = st.columns(2)
        with col1:
            paper_size = st.selectbox("Paper size", [""] + PAPER_SIZES)
        with col2:
            paper_type = st.selectbox("Paper type", [""] + PAPER_TYPES)

        date_started = None
        date_finished = None
        if status != "Not started":
            date_started = st.date_input("Date started")
        if status == "Complete":
            date_finished = st.date_input("Date finished")

        inspiration_category = st.selectbox("Inspiration source", [""] + INSPIRATION_CATEGORIES)
        inspiration_note = st.text_area("Inspiration note", placeholder="Describe what inspired you...")
        preview_image = st.file_uploader("Preview photo", type=["jpg", "jpeg", "png"])

        submitted = st.form_submit_button("Save Painting")
        if submitted:
            if not title:
                st.error("Please enter a painting title.")
            else:
                series_id = series_options.get(series_name)
                image_path = None
                if preview_image:
                    image_path = os.path.join(IMAGES_DIR, f"painting_preview_{title}_{preview_image.name}")
                    with open(image_path, "wb") as f:
                        f.write(preview_image.getbuffer())
                conn.execute("""
                    INSERT INTO paintings (
                        title, status, date_started, date_finished, paper_size, paper_type,
                        genre, subject, style, mood, series_id,
                        inspiration_category, inspiration_note, image_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    title, status,
                    str(date_started) if date_started else None,
                    str(date_finished) if date_finished else None,
                    paper_size, paper_type, genre, subject,
                    ", ".join(style), ", ".join(mood), series_id,
                    inspiration_category, inspiration_note, image_path
                ))
                conn.commit()
                st.success(f"Painting '{title}' saved successfully!")

conn.close()