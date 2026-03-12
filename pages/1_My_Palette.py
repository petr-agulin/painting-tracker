import streamlit as st
from database import get_connection
import json
import os

st.set_page_config(page_title="My Palette", page_icon="🎨")
st.title("🎨 My Paint Palette")

conn = get_connection()

db_path = os.path.join(os.path.dirname(__file__), "..", "paints_database.json")
with open(db_path, "r") as f:
    paint_db = json.load(f)

brand_names = [b["brand"] for b in paint_db["brands"]]

tab1, tab2, tab3 = st.tabs(["Add from Database", "Add Manually", "My Palette"])

with tab1:
    st.subheader("Find a paint from your tube")
    st.markdown("Select your brand, then search by color name or number printed on the tube.")

    selected_brand = st.selectbox("Brand", brand_names, key="db_brand")
    brand_data = next(b for b in paint_db["brands"] if b["brand"] == selected_brand)
    paints = brand_data["paints"]

    search = st.text_input("Search by name or code", placeholder="e.g. Ultramarine or 496")
    if search:
        paints = [p for p in paints if search.lower() in p["name"].lower() or search.lower() in p["code"].lower()]

    if not paints:
        st.info("No paints found. Try a different search term.")
    else:
        for paint in paints:
            col1, col2, col3 = st.columns([1, 4, 2])
            with col1:
                st.markdown(
                    f'<div style="background-color:{paint["hex"]};width:40px;height:40px;border-radius:4px;border:1px solid #ccc"></div>',
                    unsafe_allow_html=True
                )
            with col2:
                st.markdown(f"**{paint['name']}** — {paint['code']}")
                st.caption(f"Pigments: {paint['pigments']}")
            with col3:
                if st.button("Add to my palette", key=f"add_{selected_brand}_{paint['code']}"):
                    existing = conn.execute(
                        "SELECT id FROM paints WHERE name = ? AND brand = ?",
                        (paint["name"], selected_brand)
                    ).fetchone()
                    if existing:
                        st.warning("Already in your palette.")
                    else:
                        conn.execute(
                            "INSERT INTO paints (name, hex_color, brand) VALUES (?, ?, ?)",
                            (paint["name"], paint["hex"], selected_brand)
                        )
                        conn.commit()
                        st.success(f"Added {paint['name']}!")

with tab2:
    st.subheader("Add a paint manually")
    st.markdown("For paints not in the database, or to correct a color.")

    with st.form("manual_paint_form"):
        manual_name = st.text_input("Paint name *", placeholder="e.g. Ultramarine Blue")
        manual_brand = st.text_input("Brand", placeholder="e.g. Schmincke Horadam")
        manual_color = st.color_picker("Pick color", "#2E3192")
        submitted = st.form_submit_button("Add to my palette")
        if submitted:
            if not manual_name:
                st.error("Please enter a paint name.")
            else:
                conn.execute(
                    "INSERT INTO paints (name, hex_color, brand) VALUES (?, ?, ?)",
                    (manual_name, manual_color, manual_brand)
                )
                conn.commit()
                st.success(f"Added {manual_name} to your palette!")

with tab3:
    st.subheader("My current palette")
    my_paints = conn.execute("SELECT * FROM paints ORDER BY brand, name").fetchall()

    if not my_paints:
        st.info("Your palette is empty. Add paints from the database or manually.")
    else:
        brands_in_palette = list(dict.fromkeys(p["brand"] for p in my_paints))
        for brand in brands_in_palette:
            st.markdown(f"**{brand or 'Other'}**")
            brand_paints = [p for p in my_paints if p["brand"] == brand]
            for paint in brand_paints:
                col1, col2, col3 = st.columns([1, 4, 2])
                with col1:
                    st.markdown(
                        f'<div style="background-color:{paint["hex_color"]};width:40px;height:40px;border-radius:4px;border:1px solid #ccc"></div>',
                        unsafe_allow_html=True
                    )
                with col2:
                    st.markdown(f"**{paint['name']}**")
                    st.caption(paint["brand"] or "")
                with col3:
                    if st.button("Remove", key=f"remove_{paint['id']}"):
                        conn.execute("DELETE FROM paints WHERE id = ?", (paint["id"],))
                        conn.commit()
                        st.success(f"Removed {paint['name']} from your palette.")
                        st.rerun()

conn.close()