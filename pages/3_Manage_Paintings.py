import streamlit as st
from database import get_connection
from config import (
    PAPER_SIZES, GENRES,
    INSPIRATION_CATEGORIES, STATUS_OPTIONS
)
import os
import base64

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

st.set_page_config(page_title="Manage Paintings", page_icon="🖼️")
st.title("🖼️ Manage Paintings")

st.markdown("""
Add new paintings and manage existing ones. A painting is the starting point — log sessions against it each time you sit down to work on it. Fill in as much or as little as you like; only the title is required.
""")

conn = get_connection()

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# Reset all editing states when page loads fresh
if "paintings_page_loaded" not in st.session_state:
    st.session_state["paintings_page_loaded"] = True
    for key in list(st.session_state.keys()):
        if key.startswith("editing_") or key.startswith("confirm_delete_"):
            st.session_state[key] = False

tab1, tab2 = st.tabs(["Edit / Delete Paintings", "Add New Painting"])

with tab1:
    paintings = conn.execute("SELECT * FROM paintings ORDER BY title").fetchall()

    if not paintings:
        st.info("No paintings yet. Add one in the Add New Painting tab.")
    else:
        for painting in paintings:
            session_count = conn.execute(
                "SELECT COUNT(*) as c FROM sessions WHERE painting_id = ?",
                (painting["id"],)
            ).fetchone()["c"]

            editing = st.session_state.get(f"editing_{painting['id']}", False)

            with st.expander(f"🖼️ {painting['title']} — {painting['status']}"):
                if not editing:
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
                        st.write(f"**Sessions:** {session_count}")

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