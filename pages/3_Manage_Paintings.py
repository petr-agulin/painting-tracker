import streamlit as st
from database import get_connection
from config import (
    PAPER_SIZES, PAPER_TYPES, GENRES,
    STYLES, MOODS, INSPIRATION_CATEGORIES, STATUS_OPTIONS
)

st.set_page_config(page_title="Manage Paintings", page_icon="🖼️")
st.title("🖼️ Manage Paintings")

conn = get_connection()

tab1, tab2 = st.tabs(["Add New Painting", "Edit / Delete Paintings"])

with tab1:
    series_rows = conn.execute("SELECT id, name FROM series").fetchall()
    series_options = {"-- No series --": None}
    series_options.update({row["name"]: row["id"] for row in series_rows})

    with st.form("new_painting_form"):
        title = st.text_input("Painting title *", placeholder="e.g. Morning Light on the Canal")
        col1, col2 = st.columns(2)
        with col1:
            status = st.selectbox("Status *", STATUS_OPTIONS)
            date_started = st.date_input("Date started")
            paper_size = st.selectbox("Paper size", [""] + PAPER_SIZES)
            paper_type = st.selectbox("Paper type", [""] + PAPER_TYPES)
            genre = st.selectbox("Genre", [""] + GENRES)
        with col2:
            subject = st.text_input("Subject", placeholder="e.g. Canal in Amsterdam at dawn")
            style = st.selectbox("Style", [""] + STYLES)
            mood = st.selectbox("Mood / color temperature", [""] + MOODS)
            series_name = st.selectbox("Series", list(series_options.keys()))
        inspiration_category = st.selectbox("Inspiration source", [""] + INSPIRATION_CATEGORIES)
        inspiration_note = st.text_area("Inspiration note", placeholder="Describe what inspired you...")
        submitted = st.form_submit_button("Save Painting")
        if submitted:
            if not title:
                st.error("Please enter a painting title.")
            else:
                series_id = series_options.get(series_name)
                conn.execute("""
                    INSERT INTO paintings (
                        title, status, date_started, paper_size, paper_type,
                        genre, subject, style, mood, series_id,
                        inspiration_category, inspiration_note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    title, status, str(date_started),
                    paper_size, paper_type, genre, subject,
                    style, mood, series_id,
                    inspiration_category, inspiration_note
                ))
                conn.commit()
                st.success(f"Painting '{title}' saved successfully!")

with tab2:
    paintings = conn.execute("SELECT * FROM paintings ORDER BY title").fetchall()
    if not paintings:
        st.info("No paintings yet. Add one in the first tab.")
    else:
        for painting in paintings:
            session_count = conn.execute(
                "SELECT COUNT(*) as c FROM sessions WHERE painting_id = ?",
                (painting["id"],)
            ).fetchone()["c"]

            with st.expander(f"🖼️ {painting['title']} — {painting['status']}"):
                edit_key = f"edit_{painting['id']}"
                if st.button("Edit this painting", key=edit_key):
                    st.session_state[f"editing_{painting['id']}"] = True

                if st.session_state.get(f"editing_{painting['id']}"):
                    series_rows = conn.execute("SELECT id, name FROM series").fetchall()
                    series_options_edit = {"-- No series --": None}
                    series_options_edit.update({row["name"]: row["id"] for row in series_rows})
                    current_series = next(
                        (name for name, sid in series_options_edit.items() if sid == painting["series_id"]),
                        "-- No series --"
                    )

                    with st.form(f"edit_form_{painting['id']}"):
                        new_title = st.text_input("Title *", value=painting["title"])
                        col1, col2 = st.columns(2)
                        with col1:
                            new_status = st.selectbox("Status", STATUS_OPTIONS,
                                index=STATUS_OPTIONS.index(painting["status"]) if painting["status"] in STATUS_OPTIONS else 0)
                            new_date = st.text_input("Date started", value=painting["date_started"] or "")
                            new_size = st.selectbox("Paper size", [""] + PAPER_SIZES,
                                index=([""] + PAPER_SIZES).index(painting["paper_size"]) if painting["paper_size"] in PAPER_SIZES else 0)
                            new_type = st.selectbox("Paper type", [""] + PAPER_TYPES,
                                index=([""] + PAPER_TYPES).index(painting["paper_type"]) if painting["paper_type"] in PAPER_TYPES else 0)
                            new_genre = st.selectbox("Genre", [""] + GENRES,
                                index=([""] + GENRES).index(painting["genre"]) if painting["genre"] in GENRES else 0)
                        with col2:
                            new_subject = st.text_input("Subject", value=painting["subject"] or "")
                            new_style = st.selectbox("Style", [""] + STYLES,
                                index=([""] + STYLES).index(painting["style"]) if painting["style"] in STYLES else 0)
                            new_mood = st.selectbox("Mood", [""] + MOODS,
                                index=([""] + MOODS).index(painting["mood"]) if painting["mood"] in MOODS else 0)
                            new_series = st.selectbox("Series", list(series_options_edit.keys()),
                                index=list(series_options_edit.keys()).index(current_series))
                        new_inspiration_cat = st.selectbox("Inspiration source", [""] + INSPIRATION_CATEGORIES,
                            index=([""] + INSPIRATION_CATEGORIES).index(painting["inspiration_category"]) if painting["inspiration_category"] in INSPIRATION_CATEGORIES else 0)
                        new_inspiration_note = st.text_area("Inspiration note", value=painting["inspiration_note"] or "")
                        save_edit = st.form_submit_button("Save changes")
                        if save_edit:
                            if not new_title:
                                st.error("Title cannot be empty.")
                            else:
                                conn.execute("""
                                    UPDATE paintings SET
                                        title=?, status=?, date_started=?, paper_size=?,
                                        paper_type=?, genre=?, subject=?, style=?, mood=?,
                                        series_id=?, inspiration_category=?, inspiration_note=?
                                    WHERE id=?
                                """, (
                                    new_title, new_status, new_date, new_size,
                                    new_type, new_genre, new_subject, new_style, new_mood,
                                    series_options_edit.get(new_series),
                                    new_inspiration_cat, new_inspiration_note,
                                    painting["id"]
                                ))
                                conn.commit()
                                st.session_state[f"editing_{painting['id']}"] = False
                                st.success("Painting updated successfully!")
                                st.rerun()

                st.markdown("---")
                if session_count > 0:
                    st.warning(f"Deleting this painting will also delete {session_count} linked session(s).")
                if st.button("Delete this painting", key=f"delete_{painting['id']}"):
                    st.session_state[f"confirm_delete_{painting['id']}"] = True

                if st.session_state.get(f"confirm_delete_{painting['id']}"):
                    st.error(f"Are you sure you want to delete '{painting['title']}'? This cannot be undone.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Yes, delete", key=f"yes_delete_{painting['id']}"):
                            conn.execute("DELETE FROM sessions WHERE painting_id = ?", (painting["id"],))
                            conn.execute("DELETE FROM paintings WHERE id = ?", (painting["id"],))
                            conn.commit()
                            st.session_state[f"confirm_delete_{painting['id']}"] = False
                            st.success("Painting deleted.")
                            st.rerun()
                    with col2:
                        if st.button("Cancel", key=f"cancel_delete_{painting['id']}"):
                            st.session_state[f"confirm_delete_{painting['id']}"] = False
                            st.rerun()

conn.close()