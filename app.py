import streamlit as st
from database import initialize_database

initialize_database()

st.set_page_config(
    page_title="Painting Tracker",
    page_icon="🎨",
    layout="wide"
)

st.title("🎨 Painting Tracker")
st.markdown("Welcome to your personal watercolor painting journal.")

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Paintings", "0")

with col2:
    st.metric("Total Sessions", "0")

with col3:
    st.metric("Total Hours", "0")

st.markdown("---")
st.subheader("What would you like to do?")
st.markdown("Use the **sidebar on the left** to navigate between sections.")