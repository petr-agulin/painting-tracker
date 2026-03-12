import streamlit as st
from database import get_connection

st.set_page_config(page_title="Series", page_icon="📚")
st.title("📚 Manage Series")

conn = get_connection()

tab1, tab2 = st.tabs(["Add New Series", "View All Series"])

with tab1:
    st.subheader("Create a new series")
    with st.form("new_series_form"):
        name = st.text_input("Series name *", placeholder="e.g. Amsterdam Canals")
        concept = st.text_area("Concept / description", placeholder="What is this series about?")
        target_paintings = st.number_input("Target number of paintings", min_value=0, value=0)
        date_started = st.date_input("Date started")
        submitted = st.form_submit_button("Save Series")
        if submitted:
            if not name:
                st.error("Please enter a series name.")
            else:
                conn.execute(
                    "INSERT INTO series (name, concept, target_paintings, date_started) VALUES (?, ?, ?, ?)",
                    (name, concept, target_paintings, str(date_started))
                )
                conn.commit()
                st.success(f"Series '{name}' saved successfully!")

with tab2:
    st.subheader("All series")
    series = conn.execute("SELECT * FROM series ORDER BY date_started DESC").fetchall()
    if not series:
        st.info("No series yet. Create your first series above.")
    else:
        for s in series:
            painting_count = conn.execute(
                "SELECT COUNT(*) as c FROM paintings WHERE series_id = ?",
                (s["id"],)
            ).fetchone()["c"]
            with st.expander(f"📚 {s['name']}"):
                st.write(f"**Concept:** {s['concept'] or 'not set'}")
                st.write(f"**Target paintings:** {s['target_paintings'] or 'not set'}")
                st.write(f"**Started:** {s['date_started'] or 'not set'}")
                st.write(f"**Paintings in this series:** {painting_count}")
                if s["target_paintings"]:
                    progress = min(painting_count / s["target_paintings"], 1.0)
                    st.progress(progress, text=f"{painting_count} of {s['target_paintings']} paintings")

conn.close()