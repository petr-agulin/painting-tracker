import streamlit as st
from database import get_connection
import json
import os
from PIL import Image

st.set_page_config(page_title="My Palette", page_icon="🎨")
st.title("🎨 My Palette")

st.markdown("""
Your personal paint hub. Browse the paint database and build your collection.
""")

conn = get_connection()

db_path = os.path.join(os.path.dirname(__file__), "..", "paints_database.json")
with open(db_path, "r") as f:
    paint_db = json.load(f)

brand_names = [b["brand"] for b in paint_db["brands"]]

FORM_OPTIONS = ["", "Tube", "Half pan", "Full pan", "Other"]
AMOUNT_OPTIONS = ["", "Full", "Half", "Low", "Empty"]
LIGHTFASTNESS_OPTIONS = ["", "Excellent (ASTM I)", "Very good (ASTM II)", "Fair (ASTM III)", "Poor (ASTM IV)", "Not rated"]
TRANSPARENCY_OPTIONS = ["", "Transparent", "Semi-transparent", "Opaque"]
GRANULATION_OPTIONS = ["", "None", "Slight", "Strong"]
STAINING_OPTIONS = ["", "Non-staining", "Slight", "Staining"]
REWETTABILITY_OPTIONS = ["", "Good", "Moderate", "Poor"]
REPURCHASE_OPTIONS = ["", "Yes", "No", "Maybe"]

@st.dialog("Paint Details", width="large")
def paint_detail_modal(paint_id):
    conn = get_connection()
    paint = conn.execute("SELECT * FROM paints WHERE id = ?", (paint_id,)).fetchone()
    if not paint:
        st.error("Paint not found.")
        return

    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown(
            f'<div style="background-color:{paint["hex_color"]};width:60px;height:60px;border-radius:8px;border:1px solid #ccc"></div>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(f"## {paint['name']}")
        st.markdown(f"**Brand:** {paint['brand'] or '—'}")

    st.markdown("---")

    with st.form(f"modal_form_{paint_id}"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Paint properties**")
            form = st.selectbox("Form", FORM_OPTIONS,
                index=FORM_OPTIONS.index(paint["form"]) if paint["form"] in FORM_OPTIONS else 0)
            amount = st.selectbox("Amount remaining", AMOUNT_OPTIONS,
                index=AMOUNT_OPTIONS.index(paint["amount_remaining"]) if paint["amount_remaining"] in AMOUNT_OPTIONS else 0)
            pigments = st.text_input("Pigments", value=paint["pigments"] or "",
                placeholder="e.g. PB29, PY43")
            lightfastness = st.selectbox("Lightfastness", LIGHTFASTNESS_OPTIONS,
                index=LIGHTFASTNESS_OPTIONS.index(paint["lightfastness"]) if paint["lightfastness"] in LIGHTFASTNESS_OPTIONS else 0,
                help="How resistant this color is to fading. ASTM I is archival quality. ASTM III or IV will fade.")
            transparency = st.selectbox("Transparency", TRANSPARENCY_OPTIONS,
                index=TRANSPARENCY_OPTIONS.index(paint["transparency"]) if paint["transparency"] in TRANSPARENCY_OPTIONS else 0,
                help="Whether light passes through the paint to the paper. Transparent paints glow. Opaque paints cover.")
            granulation = st.selectbox("Granulation", GRANULATION_OPTIONS,
                index=GRANULATION_OPTIONS.index(paint["granulation"]) if paint["granulation"] in GRANULATION_OPTIONS else 0,
                help="Whether pigment particles settle into paper texture creating a sandy effect.")
            staining = st.selectbox("Staining", STAINING_OPTIONS,
                index=STAINING_OPTIONS.index(paint["staining"]) if paint["staining"] in STAINING_OPTIONS else 0,
                help="Whether pigment permanently bonds with paper. Staining paints cannot be lifted once dry.")
            rewettability = st.selectbox("Rewettability", REWETTABILITY_OPTIONS,
                index=REWETTABILITY_OPTIONS.index(paint["rewettability"]) if paint["rewettability"] in REWETTABILITY_OPTIONS else 0,
                help="How easily dried pan paint reactivates with a wet brush.")
        with col2:
            st.markdown("**Personal**")
            price = st.number_input("Price paid", min_value=0.0,
                value=float(paint["price_paid"]) if paint["price_paid"] else 0.0,
                step=0.5)
            date_purchased = st.text_input("Date purchased",
                value=paint["date_purchased"] or "", placeholder="e.g. 2024-03")
            where_purchased = st.text_input("Where purchased",
                value=paint["where_purchased"] or "", placeholder="e.g. Gerstaecker Stockholm")
            repurchase = st.selectbox("Would repurchase", REPURCHASE_OPTIONS,
                index=REPURCHASE_OPTIONS.index(paint["would_repurchase"]) if paint["would_repurchase"] in REPURCHASE_OPTIONS else 0)
            notes = st.text_area("Personal notes", value=paint["notes"] or "",
                placeholder="What you like, what's difficult, what subjects or moods it suits...")

        col1, col2, col3 = st.columns(3)
        with col1:
            save = st.form_submit_button("Save")
        with col2:
            cancel = st.form_submit_button("Cancel")
        with col3:
            remove = st.form_submit_button("Remove from collection")

        if save:
            conn.execute("""
                UPDATE paints SET
                    form=?, amount_remaining=?, pigments=?, lightfastness=?,
                    transparency=?, granulation=?, staining=?, rewettability=?,
                    price_paid=?, date_purchased=?, where_purchased=?,
                    would_repurchase=?, notes=?
                WHERE id=?
            """, (
                form, amount, pigments, lightfastness,
                transparency, granulation, staining, rewettability,
                price if price > 0 else None,
                date_purchased, where_purchased,
                repurchase, notes, paint_id
            ))
            conn.commit()
            st.success("Paint details saved!")
            st.rerun()

        if cancel:
            st.rerun()

        if remove:
            conn.execute("DELETE FROM paints WHERE id = ?", (paint_id,))
            conn.commit()
            st.rerun()


tab1, tab2, tab3 = st.tabs(["My Palette", "Paint Database", "Add Paint Manually"])

# ── Tab 1: My Palette ─────────────────────────────────────────

with tab1:
    st.subheader("My paint collection")
    my_paints = conn.execute("SELECT * FROM paints ORDER BY brand, name").fetchall()

    if not my_paints:
        st.info("Your collection is empty. Add paints from the Paint Database tab.")
    else:
        brands_in_palette = list(dict.fromkeys(p["brand"] for p in my_paints))
        for brand in brands_in_palette:
            st.markdown(f"**{brand or 'Other'}**")
            brand_paints = [p for p in my_paints if p["brand"] == brand]
            for paint in brand_paints:
                col1, col2, col3, col4, col5, col6 = st.columns([1, 3, 2, 2, 2, 3])
                with col1:
                    st.markdown(
                        f'<div style="background-color:{paint["hex_color"]};width:32px;height:32px;border-radius:4px;border:1px solid #ccc;margin-top:4px"></div>',
                        unsafe_allow_html=True
                    )
                with col2:
                    st.markdown(f"**{paint['name']}**")
                with col3:
                    st.caption(paint["form"] or "—")
                with col4:
                    st.caption(paint["amount_remaining"] or "—")
                with col5:
                    st.caption(paint["date_purchased"] or "—")
                with col6:
                    if st.button("View / Edit / Remove", key=f"view_paint_{paint['id']}", use_container_width=True):
                        paint_detail_modal(paint["id"])
            st.markdown("---")

# ── Tab 2: Paint Database ─────────────────────────────────────

with tab2:
    st.subheader("Browse & add paints")
    col1, col2 = st.columns(2)
    with col1:
        selected_brand = st.selectbox("Brand", brand_names, key="db_brand")
    with col2:
        if st.session_state.pop("do_clear_search", False):
            st.session_state["search_counter"] = st.session_state.get("search_counter", 0) + 1
        s1, s2 = st.columns([5, 1])
        with s1:
            st.text_input(
                "Search by name or code",
                placeholder="e.g. Ivory Black or PB29 — searches all brands",
                key=f"db_search_val_{st.session_state.get('search_counter', 0)}"
            )
        with s2:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("✕", key="clear_search", help="Clear search"):
                st.session_state["do_clear_search"] = True
                st.rerun()

    my_paints_check = conn.execute("SELECT name, brand FROM paints").fetchall()
    my_paints_set = {(p["name"], p["brand"]) for p in my_paints_check}

    search_term = st.session_state.get(f"db_search_val_{st.session_state.get('search_counter', 0)}", "")
    if search_term:
        paints_with_brand = []
        for brand in paint_db["brands"]:
            for p in brand["paints"]:
                if search_term.lower() in p["name"].lower() or search_term.lower() in p["code"].lower():
                    paints_with_brand.append((p, brand["brand"]))
    else:
        brand_data = next(b for b in paint_db["brands"] if b["brand"] == selected_brand)
        paints_with_brand = [(p, selected_brand) for p in brand_data["paints"]]

    if not paints_with_brand:
        st.info("No paints found. Try a different search term.")
    else:
        if search_term:
            st.caption(f"{len(paints_with_brand)} result(s) across all brands")
        for paint, brand in paints_with_brand:
            in_collection = (paint["name"], brand) in my_paints_set
            col1, col2, col3 = st.columns([1, 4, 2])
            with col1:
                if in_collection:
                    st.markdown(
                        f'<div style="position:relative;width:40px;height:40px">'
                        f'<div style="background-color:{paint["hex"]};width:40px;height:40px;border-radius:4px;border:1px solid #ccc"></div>'
                        f'<div style="position:absolute;top:0;left:0;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-size:20px;color:#fff;text-shadow:0 0 3px #000">✓</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div style="background-color:{paint["hex"]};width:40px;height:40px;border-radius:4px;border:1px solid #ccc"></div>',
                        unsafe_allow_html=True
                    )
            with col2:
                st.markdown(f"**{paint['name']}** — {paint['code']}")
                st.caption(f"{brand} · Pigments: {paint['pigments']}")
            with col3:
                if in_collection:
                    st.markdown('<span style="color:#5a8a5a;font-weight:500">Added</span>', unsafe_allow_html=True)
                else:
                    if st.button("Add to my collection", key=f"add_{brand}_{paint['name']}"):
                        conn.execute(
                            "INSERT INTO paints (name, hex_color, brand) VALUES (?, ?, ?)",
                            (paint["name"], paint["hex"], brand)
                        )
                        conn.commit()
                        st.rerun()

# ── Tab 3: Add Paint Manually ─────────────────────────────────

with tab3:
    st.subheader("Add a paint manually")
    st.markdown("For paints not in the database.")

    if st.session_state.pop("reset_manual_form", False):
        st.session_state["manual_color_picker"] = "#888888"
        st.session_state["prev_manual_color"] = "#888888"
        st.session_state["manual_name_input"] = ""
        st.session_state.pop("manual_brand", None)
        st.session_state.pop("manual_pigments", None)

    if "prev_manual_color" not in st.session_state:
        st.session_state["prev_manual_color"] = "#888888"
    if "manual_name_input" not in st.session_state:
        st.session_state["manual_name_input"] = ""

    if st.session_state.pop("show_add_success", None):
        st.success("✓ Paint added to your collection.")

    manual_color = st.color_picker("Pick color", st.session_state["prev_manual_color"], key="manual_color_picker")

    if manual_color != st.session_state["prev_manual_color"]:
        st.session_state["prev_manual_color"] = manual_color
        st.session_state["manual_name_input"] = manual_color.upper()

    manual_name = st.text_input("Paint name *", key="manual_name_input", placeholder="e.g. Ultramarine Blue")
    manual_brand = st.text_input("Brand", placeholder="e.g. Schmincke Horadam", key="manual_brand")
    manual_pigments = st.text_input("Pigments", placeholder="e.g. PB29", key="manual_pigments")

    if st.button("Add to my collection", key="manual_add_btn"):
        if not manual_name:
            st.error("Please enter a paint name.")
        else:
            conn.execute(
                "INSERT INTO paints (name, hex_color, brand) VALUES (?, ?, ?)",
                (manual_name, manual_color, manual_brand)
            )
            conn.commit()
            st.session_state["reset_manual_form"] = True
            st.session_state["show_add_success"] = True
            st.rerun()

conn.close()
