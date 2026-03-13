import streamlit as st
from database import get_connection

st.set_page_config(page_title="Manage Series", page_icon="📚")
st.title("📚 Manage Series")

st.markdown("""
Organize your paintings into series — a group of works sharing a common concept, theme, or intention. A series is optional; paintings can exist without one. Need inspiration for naming? Consider something like *Quiet Waters*, *Light Through February*, or *The Harbour at Dusk*.
""")

conn = get_connection()

tab1, tab2 = st.tabs(["Add New Series", "Edit / Delete Series"])

with tab1:
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
    series = conn.execute("SELECT * FROM series ORDER BY name").fetchall()
    if not series:
        st.info("No series yet. Add one in the first tab.")
    else:
        for s in series:
            painting_count = conn.execute(
                "SELECT COUNT(*) as c FROM paintings WHERE series_id = ?",
                (s["id"],)
            ).fetchone()["c"]

            with st.expander(f"📚 {s['name']}"):
                if st.button("Edit this series", key=f"edit_{s['id']}"):
                    st.session_state[f"editing_series_{s['id']}"] = True

                if st.session_state.get(f"editing_series_{s['id']}"):
                    with st.form(f"edit_series_form_{s['id']}"):
                        new_name = st.text_input("Series name *", value=s["name"])
                        new_concept = st.text_area("Concept / description", value=s["concept"] or "")
                        new_target = st.number_input("Target number of paintings", min_value=0, value=s["target_paintings"] or 0)
                        new_date = st.text_input("Date started", value=s["date_started"] or "")
                        save_edit = st.form_submit_button("Save changes")
                        if save_edit:
                            if not new_name:
                                st.error("Series name cannot be empty.")
                            else:
                                conn.execute("""
                                    UPDATE series SET name=?, concept=?, target_paintings=?, date_started=?
                                    WHERE id=?
                                """, (new_name, new_concept, new_target, new_date, s["id"]))
                                conn.commit()
                                st.session_state[f"editing_series_{s['id']}"] = False
                                st.success("Series updated successfully!")
                                st.rerun()

                st.markdown("---")
                if painting_count > 0:
                    st.warning(f"This series has {painting_count} linked painting(s). Deleting it will remove the series but keep all paintings.")
                if st.button("Delete this series", key=f"delete_{s['id']}"):
                    st.session_state[f"confirm_delete_series_{s['id']}"] = True

                if st.session_state.get(f"confirm_delete_series_{s['id']}"):
                    st.error(f"Are you sure you want to delete '{s['name']}'? This cannot be undone.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Yes, delete", key=f"yes_delete_series_{s['id']}"):
                            conn.execute(
                                "UPDATE paintings SET series_id = NULL WHERE series_id = ?",
                                (s["id"],)
                            )
                            conn.execute("DELETE FROM series WHERE id = ?", (s["id"],))
                            conn.commit()
                            st.session_state[f"confirm_delete_series_{s['id']}"] = False
                            st.success("Series deleted. Linked paintings have been kept.")
                            st.rerun()
                    with col2:
                        if st.button("Cancel", key=f"cancel_delete_series_{s['id']}"):
                            st.session_state[f"confirm_delete_series_{s['id']}"] = False
                            st.rerun()

conn.close()