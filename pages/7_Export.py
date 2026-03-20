import streamlit as st
from database import get_connection
import pandas as pd
import io

st.set_page_config(page_title="Export", page_icon="📥")
st.title("📥 Export Your Data")
st.markdown("""
Download your painting history as a CSV file for backup or further analysis.
""")

conn = get_connection()

paintings = conn.execute("SELECT * FROM paintings").fetchall()

if not paintings:
    st.info("No paintings yet. Add some paintings and sessions first.")
    st.stop()

painting_options = {row["title"]: row["id"] for row in paintings}

st.subheader("Export a single painting history")
selected_title = st.selectbox("Select a painting", list(painting_options.keys()))

if selected_title:
    painting_id = painting_options[selected_title]
    painting = conn.execute("SELECT * FROM paintings WHERE id = ?", (painting_id,)).fetchone()
    sessions = conn.execute(
        "SELECT * FROM sessions WHERE painting_id = ? ORDER BY date",
        (painting_id,)
    ).fetchall()

    painting_df = pd.DataFrame([dict(painting)])
    sessions_df = pd.DataFrame([dict(s) for s in sessions]) if sessions else pd.DataFrame()

    col1, col2 = st.columns(2)

    with col1:
        csv_buffer = io.StringIO()
        painting_df.to_csv(csv_buffer, index=False)
        if not sessions_df.empty:
            csv_buffer.write("\n\nSessions\n")
            sessions_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download as CSV",
            data=csv_buffer.getvalue(),
            file_name=f"{selected_title}_history.csv",
            mime="text/csv"
        )

    with col2:
        all_sessions_df = pd.read_sql("SELECT * FROM sessions", conn)
        all_paintings_df = pd.read_sql("SELECT * FROM paintings", conn)
        full_buffer = io.StringIO()
        full_buffer.write("PAINTINGS\n")
        all_paintings_df.to_csv(full_buffer, index=False)
        full_buffer.write("\n\nSESSIONS\n")
        all_sessions_df.to_csv(full_buffer, index=False)
        st.download_button(
            label="Download full database as CSV",
            data=full_buffer.getvalue(),
            file_name="painting_tracker_full_export.csv",
            mime="text/csv"
        )

    st.markdown("---")
    st.subheader("Painting details")
    st.write(f"**Title:** {painting['title']}")
    st.write(f"**Status:** {painting['status']}")
    st.write(f"**Started:** {painting['date_started'] or 'not set'}")
    st.write(f"**Genre:** {painting['genre'] or 'not set'}")
    st.write(f"**Style:** {painting['style'] or 'not set'}")
    st.write(f"**Inspiration:** {painting['inspiration_category'] or 'not set'}")

    if sessions:
        st.markdown("---")
        st.subheader("Session history")
        for i, s in enumerate(sessions):
            with st.expander(f"Session {i+1} — {s['date']} — Rating {s['rating']}/5"):
                st.write(f"**Duration:** {s['duration_minutes'] or 0} minutes")
                st.write(f"**Completion after session:** {s['completion_percent'] or 0}%")
                st.write(f"**What I worked on:** {s['what_worked_on'] or 'not noted'}")
                st.write(f"**What worked:** {s['what_worked'] or 'not noted'}")
                st.write(f"**What did not work:** {s['what_didnt_work'] or 'not noted'}")
                st.write(f"**Do differently:** {s['do_differently'] or 'not noted'}")
                st.write(f"**Notes:** {s['notes'] or 'none'}")
                if s["image_path"]:
                    st.image(s["image_path"], width=300)
    else:
        st.info("No sessions logged for this painting yet.")

conn.close()