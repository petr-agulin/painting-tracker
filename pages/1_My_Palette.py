import streamlit as st
from database import get_connection
import json
import os
import base64
from PIL import Image
import io
import math
from itertools import combinations

try:
    from streamlit_image_coordinates import streamlit_image_coordinates
    IMAGE_COORDS_AVAILABLE = True
except ImportError:
    IMAGE_COORDS_AVAILABLE = False

st.set_page_config(page_title="My Palette", page_icon="🎨")
st.title("🎨 My Palette")

st.markdown("""
Your personal paint hub. Browse the paint database, build your collection, and use the Color Finder to identify colors from reference images and discover how to mix them with what you own.
""")

conn = get_connection()

db_path = os.path.join(os.path.dirname(__file__), "..", "paints_database.json")
with open(db_path, "r") as f:
    paint_db = json.load(f)

brand_names = [b["brand"] for b in paint_db["brands"]]
all_paints_flat = []
for brand in paint_db["brands"]:
    for paint in brand["paints"]:
        all_paints_flat.append({**paint, "brand": brand["brand"]})

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_lab(r, g, b):
    r, g, b = r/255.0, g/255.0, b/255.0
    r = ((r+0.055)/1.055)**2.4 if r > 0.04045 else r/12.92
    g = ((g+0.055)/1.055)**2.4 if g > 0.04045 else g/12.92
    b = ((b+0.055)/1.055)**2.4 if b > 0.04045 else b/12.92
    x = (r*0.4124 + g*0.3576 + b*0.1805) / 0.95047
    y = (r*0.2126 + g*0.7152 + b*0.0722) / 1.00000
    z = (r*0.0193 + g*0.1192 + b*0.9505) / 1.08883
    x = x**0.3333 if x > 0.008856 else 7.787*x + 16/116
    y = y**0.3333 if y > 0.008856 else 7.787*y + 16/116
    z = z**0.3333 if z > 0.008856 else 7.787*z + 16/116
    return (116*y - 16, 500*(x-y), 200*(y-z))

def color_distance(hex1, hex2):
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    l1, a1, b1_lab = rgb_to_lab(r1, g1, b1)
    l2, a2, b2_lab = rgb_to_lab(r2, g2, b2)
    return math.sqrt((l1-l2)**2 + (a1-a2)**2 + (b1_lab-b2_lab)**2)

def color_distance_hue_weighted(hex1, hex2, hue_weight=3.0):
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    l1, a1, b1_lab = rgb_to_lab(r1, g1, b1)
    l2, a2, b2_lab = rgb_to_lab(r2, g2, b2)
    lightness_dist = (l1 - l2) ** 2
    hue_dist = hue_weight * ((a1 - a2) ** 2 + (b1_lab - b2_lab) ** 2)
    return math.sqrt(lightness_dist + hue_dist)

def get_hue_family(hex_color):
    r, g, b = hex_to_rgb(hex_color)
    _, a, b_lab = rgb_to_lab(r, g, b)
    chroma = math.sqrt(a**2 + b_lab**2)
    if chroma < 8:
        return "neutral"
    angle = math.degrees(math.atan2(b_lab, a)) % 360
    if angle < 30 or angle >= 330:
        return "red"
    elif angle < 90:
        return "yellow"
    elif angle < 150:
        return "green"
    elif angle < 210:
        return "cyan"
    elif angle < 270:
        return "blue"
    elif angle < 330:
        return "purple"
    return "neutral"

def rgb_to_hex(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def find_best_matches_by_hue_family(target_hex, paint_list, top_n=5):
    target_family = get_hue_family(target_hex)
    family_matches = []
    other_matches = []
    for paint in paint_list:
        hex_val = paint["hex_color"] if "hex_color" in paint else paint["hex"]
        dist = color_distance(target_hex, hex_val)
        paint_family = get_hue_family(hex_val)
        if paint_family == target_family:
            family_matches.append((dist, paint))
        else:
            other_matches.append((dist, paint))
    family_matches.sort(key=lambda x: x[0])
    other_matches.sort(key=lambda x: x[0])
    combined = family_matches[:top_n]
    if len(combined) < top_n:
        combined += other_matches[:top_n - len(combined)]
    return combined[:top_n]

def find_best_matches_combined(target_hex, paint_list, top_n=5):
    target_family = get_hue_family(target_hex)
    family_matches = []
    other_matches = []
    for paint in paint_list:
        hex_val = paint["hex_color"] if "hex_color" in paint else paint["hex"]
        dist_hue = color_distance_hue_weighted(target_hex, hex_val)
        dist_plain = color_distance(target_hex, hex_val)
        paint_family = get_hue_family(hex_val)
        if paint_family == target_family:
            family_matches.append((dist_hue, paint))
        else:
            other_matches.append((dist_hue, paint))
    family_matches.sort(key=lambda x: x[0])
    other_matches.sort(key=lambda x: x[0])
    combined = family_matches[:top_n]
    if len(combined) < top_n:
        combined += other_matches[:top_n - len(combined)]
    return combined[:top_n]

def generate_weight_sets(n, steps=10):
    if n == 1:
        return [[1.0]]
    result = []
    def recurse(remaining, depth, current):
        if depth == n - 1:
            if remaining > 0:
                current.append(remaining / steps)
                result.append(current[:])
                current.pop()
        else:
            for i in range(1, remaining):
                current.append(i / steps)
                recurse(remaining - i, depth + 1, current)
                current.pop()
    recurse(steps, 0, [])
    return result

def find_mix(target_hex, my_paints, max_colors=5):
    if not my_paints:
        return [], float("inf")
    target_r, target_g, target_b = hex_to_rgb(target_hex)
    tl, ta, tb_lab = rgb_to_lab(target_r, target_g, target_b)
    best_result = None
    best_distance = float("inf")
    paints_with_rgb = [(p, hex_to_rgb(p["hex_color"])) for p in my_paints]
    for n in range(1, min(max_colors + 1, len(paints_with_rgb) + 1)):
        weight_sets = generate_weight_sets(n, steps=10)
        for combo in combinations(paints_with_rgb, n):
            for weights in weight_sets:
                mix_r = sum(w * c[1][0] for w, c in zip(weights, combo))
                mix_g = sum(w * c[1][1] for w, c in zip(weights, combo))
                mix_b = sum(w * c[1][2] for w, c in zip(weights, combo))
                ml, ma, mb_lab = rgb_to_lab(int(mix_r), int(mix_g), int(mix_b))
                dist = math.sqrt((tl-ml)**2 + (ta-ma)**2 + (tb_lab-mb_lab)**2)
                if dist < best_distance:
                    best_distance = dist
                    best_result = [(c[0], round(w*100)) for w, c in zip(weights, combo)]
        if best_distance < 10:
            break
    return best_result, best_distance

def render_paint_matches(matches, my_paints):
    for dist, paint in matches:
        hex_val = paint["hex_color"] if "hex_color" in paint else paint["hex"]
        col1, col2, col3 = st.columns([1, 4, 1])
        with col1:
            st.markdown(
                f'<div style="background-color:{hex_val};width:40px;height:40px;border-radius:4px;border:1px solid #ccc"></div>',
                unsafe_allow_html=True
            )
        with col2:
            brand = paint.get("brand", "")
            name = paint.get("name", "")
            st.markdown(f"**{name}** — {brand}")
            in_collection = any(p["name"] == name and p["brand"] == brand for p in my_paints)
            if in_collection:
                st.caption("✅ In your collection")
            else:
                st.caption("Not in your collection")
        with col3:
            st.caption(f"Δ {int(dist)}")

tab1, tab2, tab3 = st.tabs(["Paint Database", "My Collection", "Color Finder"])

with tab1:
    st.subheader("Browse & add paints")
    col1, col2 = st.columns(2)
    with col1:
        selected_brand = st.selectbox("Brand", brand_names, key="db_brand")
    with col2:
        search = st.text_input("Search by name or code", placeholder="e.g. Ultramarine or 496")

    brand_data = next(b for b in paint_db["brands"] if b["brand"] == selected_brand)
    paints = brand_data["paints"]

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
                if st.button("Add to my collection", key=f"add_{selected_brand}_{paint['code']}"):
                    existing = conn.execute(
                        "SELECT id FROM paints WHERE name = ? AND brand = ?",
                        (paint["name"], selected_brand)
                    ).fetchone()
                    if existing:
                        st.warning("Already in your collection.")
                    else:
                        conn.execute(
                            "INSERT INTO paints (name, hex_color, brand) VALUES (?, ?, ?)",
                            (paint["name"], paint["hex"], selected_brand)
                        )
                        conn.commit()
                        st.success(f"Added {paint['name']}!")

    st.markdown("---")
    st.subheader("Add a paint manually")
    st.markdown("For paints not in the database.")
    with st.form("manual_paint_form"):
        manual_name = st.text_input("Paint name *", placeholder="e.g. Ultramarine Blue")
        manual_brand = st.text_input("Brand", placeholder="e.g. Schmincke Horadam")
        manual_color = st.color_picker("Pick color", "#2E3192")
        manual_pigments = st.text_input("Pigments", placeholder="e.g. PB29")
        submitted = st.form_submit_button("Add to my collection")
        if submitted:
            if not manual_name:
                st.error("Please enter a paint name.")
            else:
                conn.execute(
                    "INSERT INTO paints (name, hex_color, brand) VALUES (?, ?, ?)",
                    (manual_name, manual_color, manual_brand)
                )
                conn.commit()
                st.success(f"Added {manual_name} to your collection!")

with tab2:
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
                        st.success(f"Removed {paint['name']}.")
                        st.rerun()

with tab3:
    st.subheader("Color Finder")
    st.markdown("""
    Upload a reference image, click on any color you want to achieve, and the tool will suggest the closest paints from the database and how to mix them using what you own.
    """)

    if not IMAGE_COORDS_AVAILABLE:
        st.error("streamlit-image-coordinates is not installed. Run: pip install streamlit-image-coordinates")
        st.stop()

    my_paints = conn.execute("SELECT * FROM paints ORDER BY brand, name").fetchall()

    uploaded_file = st.file_uploader("Upload reference image", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image = Image.open(uploaded_file).convert("RGB")

        max_width = 700
        if image.width > max_width:
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image_display = image.resize((max_width, new_height))
        else:
            image_display = image

        st.markdown("**Click anywhere on the image to pick a color:**")
        coords = streamlit_image_coordinates(image_display, key="color_picker_image")

        if coords:
            x = min(coords["x"], image_display.width - 1)
            y = min(coords["y"], image_display.height - 1)
            pixel_color = image_display.getpixel((x, y))
            r, g, b = pixel_color[0], pixel_color[1], pixel_color[2]
            target_hex = rgb_to_hex(r, g, b)

            st.markdown("---")
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown(
                    f'<div style="background-color:{target_hex};width:60px;height:60px;border-radius:8px;border:1px solid #ccc"></div>',
                    unsafe_allow_html=True
                )
            with col2:
                st.markdown(f"**Selected color:** `{target_hex.upper()}`")
                st.markdown(f"RGB: {r}, {g}, {b}")

            st.markdown("---")
            st.markdown("**Option B — Hue family matching:**")
            st.caption("Prioritises paints in the same color family as your target.")
            matches_b = find_best_matches_by_hue_family(target_hex, all_paints_flat, top_n=5)
            render_paint_matches(matches_b, my_paints)

            st.markdown("---")
            st.markdown("**Combined — Hue family + hue-weighted ranking:**")
            st.caption("Same family priority as B, but ranked by perceptual hue accuracy within the family.")
            matches_c = find_best_matches_combined(target_hex, all_paints_flat, top_n=5)
            render_paint_matches(matches_c, my_paints)

            if my_paints:
                st.markdown("---")
                st.markdown("**Mixing suggestion using your collection:**")
                st.caption("Proportions are digital approximations — a starting point for real experimentation.")

                max_colors = st.slider("Maximum colors to mix", min_value=1, max_value=5, value=3, help="The tool will use up to this many paints to approximate your target color.")

                with st.spinner("Calculating best mix..."):
                    result, distance = find_mix(target_hex, my_paints, max_colors=max_colors)

                if result:
                    mix_r = sum((hex_to_rgb(p["hex_color"])[0] * w / 100) for p, w in result)
                    mix_g = sum((hex_to_rgb(p["hex_color"])[1] * w / 100) for p, w in result)
                    mix_b = sum((hex_to_rgb(p["hex_color"])[2] * w / 100) for p, w in result)
                    mix_hex = rgb_to_hex(mix_r, mix_g, mix_b)

                    col1, col2, col3 = st.columns([1, 1, 4])
                    with col1:
                        st.markdown(
                            f'<div style="background-color:{target_hex};width:50px;height:50px;border-radius:6px;border:1px solid #ccc"></div>',
                            unsafe_allow_html=True
                        )
                        st.caption("Target")
                    with col2:
                        st.markdown(
                            f'<div style="background-color:{mix_hex};width:50px;height:50px;border-radius:6px;border:1px solid #ccc"></div>',
                            unsafe_allow_html=True
                        )
                        st.caption("Mix result")
                    with col3:
                        for paint, weight in result:
                            p_hex = paint["hex_color"]
                            brand = paint["brand"] if paint["brand"] else ""
                            st.markdown(
                                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
                                f'<div style="background-color:{p_hex};width:24px;height:24px;border-radius:3px;border:1px solid #ccc;flex-shrink:0"></div>'
                                f'<span><b>{weight}%</b> {paint["name"]} — {brand}</span>'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                else:
                    st.info("Add paints to your collection to get mixing suggestions.")
            else:
                st.info("Add paints to your collection to get mixing suggestions.")
    else:
        st.info("Upload an image above to start picking colors.")

conn.close()