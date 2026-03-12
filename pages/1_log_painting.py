import streamlit as st
from database import get_connection
from config import (
    PAPER_SIZES, PAPER_TYPES, GENRES,
    STYLES, MOODS, INSPIRATION_CATEGORIES, STATUS_OPTIONS
)

st.set_page_config(page_title="Log Painting", page_icon="🖼️")
st.title("🖼️ Add a New Painting")

conn = get_connection()

# Load existing series for the dropdown
series_rows = conn.execute("SELECT id, name FROM series").fetchall()
series_options = {row["name"]: row["id"] for row in series_rows}
series_options["-- No series --"] = None

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

conn.close()