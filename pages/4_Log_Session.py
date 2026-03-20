import streamlit as st
from database import get_connection
from config import LOCATIONS, LIGHTING, MENTAL_STATES, TECHNIQUES, BRUSH_SIZES
import os
import json
from io import BytesIO
from PIL import Image
import math
from itertools import combinations
from datetime import datetime, date
import numpy as np
from scipy.optimize import minimize

try:
    from streamlit_image_coordinates import streamlit_image_coordinates
    IMAGE_COORDS_AVAILABLE = True
except ImportError:
    IMAGE_COORDS_AVAILABLE = False

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

st.set_page_config(page_title="Log Session", page_icon="🎨")
st.title("🎨 Log session")
st.markdown(
    "Open this page when you sit down to paint. Set up your painting and reference image, "
    "start the timer, use the color finder while you work, then fill in the details when you're done."
)

conn = get_connection()

# Ensure is_draft column exists (safe to run on every load)
try:
    conn.execute("ALTER TABLE sessions ADD COLUMN is_draft INTEGER DEFAULT 0")
    conn.commit()
except Exception:
    pass

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# Load full paint database for "closest single paints" suggestions
db_path = os.path.join(os.path.dirname(__file__), "..", "paints_database.json")
with open(db_path, "r") as f:
    paint_db = json.load(f)
all_paints_flat = []
for brand in paint_db["brands"]:
    for paint in brand["paints"]:
        all_paints_flat.append({**paint, "hex_color": paint["hex"], "brand": brand["brand"]})

# ── Color math (Kubelka-Munk subtractive mixing) ─────────────

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return f"#{int(round(r)):02x}{int(round(g)):02x}{int(round(b)):02x}"

def _srgb_to_linear(c):
    c = c / 255.0
    return (c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def _linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return (c * 12.92 * 255) if c <= 0.0031308 else ((1.055 * c ** (1 / 2.4) - 0.055) * 255)

def rgb_to_reflectance(r, g, b):
    """Convert 8-bit RGB to per-channel linear reflectance."""
    return np.array([_srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)])

def reflectance_to_rgb(ref):
    """Convert linear reflectance back to 8-bit RGB."""
    return tuple(_linear_to_srgb(c) for c in ref)

def refl_to_km(R):
    """Reflectance → Kubelka-Munk K/S ratio per channel."""
    R = np.clip(R, 1e-6, 1 - 1e-6)
    return (1 - R) ** 2 / (2 * R)

def km_to_refl(KS):
    """K/S ratio → reflectance per channel."""
    KS = np.clip(KS, 0, None)
    return 1 + KS - np.sqrt(KS ** 2 + 2 * KS)

def mix_km(hex_colors, weights):
    """Mix paints using Kubelka-Munk. Returns mixed reflectance."""
    weights = np.array(weights)
    weights = weights / weights.sum()
    km_sum = np.zeros(3)
    for h, w in zip(hex_colors, weights):
        r, g, b = hex_to_rgb(h)
        ref = rgb_to_reflectance(r, g, b)
        km_sum += w * refl_to_km(ref)
    return km_to_refl(km_sum)

def mix_km_to_hex(hex_colors, weights):
    ref = mix_km(hex_colors, weights)
    r, g, b = reflectance_to_rgb(ref)
    return rgb_to_hex(r, g, b)

def rgb_to_lab(r, g, b):
    r2 = _srgb_to_linear(r)
    g2 = _srgb_to_linear(g)
    b2 = _srgb_to_linear(b)
    x = (r2 * 0.4124 + g2 * 0.3576 + b2 * 0.1805) / 0.95047
    y = (r2 * 0.2126 + g2 * 0.7152 + b2 * 0.0722)
    z = (r2 * 0.0193 + g2 * 0.1192 + b2 * 0.9505) / 1.08883
    fx = x ** 0.3333 if x > 0.008856 else 7.787 * x + 16 / 116
    fy = y ** 0.3333 if y > 0.008856 else 7.787 * y + 16 / 116
    fz = z ** 0.3333 if z > 0.008856 else 7.787 * z + 16 / 116
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))

def lab_dist(h1, h2, hue_weight=3.0):
    r1, g1, b1 = hex_to_rgb(h1)
    r2, g2, b2 = hex_to_rgb(h2)
    l1, a1, b1l = rgb_to_lab(r1, g1, b1)
    l2, a2, b2l = rgb_to_lab(r2, g2, b2)
    return math.sqrt((l1 - l2) ** 2 + hue_weight * ((a1 - a2) ** 2 + (b1l - b2l) ** 2))

# Keep color_dist as alias for find_best_matches
color_dist = lab_dist

def hue_family(h):
    r, g, b = hex_to_rgb(h)
    _, a, bl = rgb_to_lab(r, g, b)
    c = math.sqrt(a ** 2 + bl ** 2)
    if c < 8:
        return "neutral"
    ang = math.degrees(math.atan2(bl, a)) % 360
    if ang < 30 or ang >= 330: return "red"
    elif ang < 90: return "yellow"
    elif ang < 150: return "green"
    elif ang < 210: return "cyan"
    elif ang < 270: return "blue"
    return "purple"

def find_best_matches(target_hex, paint_list, top_n=5):
    tf = hue_family(target_hex)
    fm, om = [], []
    for p in paint_list:
        hv = p.get("hex_color") or p.get("hex", "#000000")
        d = color_dist(target_hex, hv)
        (fm if hue_family(hv) == tf else om).append((d, p))
    fm.sort(key=lambda x: x[0])
    om.sort(key=lambda x: x[0])
    combined = fm[:top_n]
    if len(combined) < top_n:
        combined += om[:top_n - len(combined)]
    return combined[:top_n]

def _km_lab_dist(weights, target_lab, hex_colors):
    """Objective: LAB distance between target and KM mix."""
    ref = mix_km(hex_colors, weights)
    r, g, b = reflectance_to_rgb(ref)
    ml, ma, mbl = rgb_to_lab(int(r), int(g), int(b))
    tl, ta, tbl = target_lab
    return math.sqrt((tl - ml) ** 2 + 3 * ((ta - ma) ** 2 + (tbl - mbl) ** 2))

def find_mix(target_hex, paints, max_colors=3):
    """Find best mix using Kubelka-Munk + scipy continuous optimizer."""
    if not paints:
        return [], float("inf")

    tr, tg, tb = hex_to_rgb(target_hex)
    target_lab = rgb_to_lab(tr, tg, tb)
    hex_list = [p["hex_color"] for p in paints]

    best, best_d = None, float("inf")

    for n in range(1, min(max_colors + 1, len(paints) + 1)):
        for combo_idx in combinations(range(len(paints)), n):
            combo_paints = [paints[i] for i in combo_idx]
            combo_hexes = [hex_list[i] for i in combo_idx]

            # Initial guess: equal weights
            w0 = np.ones(n) / n
            constraints = {"type": "eq", "fun": lambda w: w.sum() - 1}
            bounds = [(0.05, 1.0)] * n

            try:
                res = minimize(
                    _km_lab_dist,
                    w0,
                    args=(target_lab, combo_hexes),
                    method="SLSQP",
                    bounds=bounds,
                    constraints=constraints,
                    options={"ftol": 1e-6, "maxiter": 200}
                )
                d = res.fun
                if d < best_d:
                    best_d = d
                    ws = res.x / res.x.sum()
                    best = [(p, max(1, round(w * 100))) for p, w in zip(combo_paints, ws)]
            except Exception:
                continue

        if best_d < 8:
            break

    return best, best_d

# ── Helpers ───────────────────────────────────────────────────

def elapsed_str(start_str):
    try:
        start = datetime.combine(date.today(), datetime.strptime(start_str, "%H:%M:%S").time())
        secs = max(0, int((datetime.now() - start).total_seconds()))
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    except Exception:
        return "—"

def duration_mins(start_str, end_str):
    try:
        s = datetime.strptime(start_str, "%H:%M:%S")
        e = datetime.strptime(end_str, "%H:%M:%S")
        return max(0, int((e - s).total_seconds() / 60))
    except Exception:
        return 0

def dur_label(mins):
    if mins >= 60:
        return f"{mins // 60}h {mins % 60}m"
    return f"{mins}m"

def reset_session_state():
    for k in [
        "log_phase", "log_draft_id", "log_start_time", "log_end_time",
        "log_painting_id", "log_painting_title", "log_painting_series",
        "log_reference_image", "log_discard_confirm",
    ]:
        st.session_state.pop(k, None)

# ── State init ────────────────────────────────────────────────

for k, v in {
    "log_phase": "setup",
    "log_draft_id": None,
    "log_start_time": None,
    "log_end_time": None,
    "log_painting_id": None,
    "log_painting_title": None,
    "log_painting_series": None,
    "log_reference_image": None,
    "log_discard_confirm": False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Draft resume on page load ─────────────────────────────────

if st.session_state.log_draft_id is None and st.session_state.log_phase == "setup":
    draft = conn.execute(
        "SELECT * FROM sessions WHERE is_draft=1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if draft:
        p = conn.execute(
            "SELECT p.id, p.title, s.name as sn FROM paintings p "
            "LEFT JOIN series s ON p.series_id=s.id WHERE p.id=?",
            (draft["painting_id"],)
        ).fetchone()
        st.session_state.log_draft_id = draft["id"]
        st.session_state.log_start_time = draft["start_time"]
        st.session_state.log_painting_id = draft["painting_id"]
        st.session_state.log_painting_title = p["title"] if p else "Unknown"
        st.session_state.log_painting_series = p["sn"] if p else None
        if draft["end_time"]:
            st.session_state.log_end_time = draft["end_time"]
            st.session_state.log_phase = "wrapup"
        else:
            st.session_state.log_phase = "active"


# ══════════════════════════════════════════════════════════════
# PHASE 1 — SETUP
# ══════════════════════════════════════════════════════════════
if st.session_state.log_phase == "setup":

    paintings = conn.execute(
        "SELECT p.id, p.title, s.name as sn FROM paintings p "
        "LEFT JOIN series s ON p.series_id=s.id ORDER BY p.title"
    ).fetchall()

    ADD_NEW = "➕ Add new painting"
    options = [p["title"] for p in paintings] + [ADD_NEW]

    chosen = st.selectbox("Choose painting", options, key="log_sel_painting")

    adding_new = chosen == ADD_NEW
    new_title, series_id_new, ser_pick = "", None, "— No series —"

    if adding_new:
        series_rows = conn.execute("SELECT id, name FROM series ORDER BY name").fetchall()
        series_map = {"— No series —": None, **{r["name"]: r["id"] for r in series_rows}}
        nc1, nc2 = st.columns(2)
        with nc1:
            new_title = st.text_input(
                "Painting title *", placeholder="e.g. Morning mist over the canal",
                key="log_new_title"
            )
        with nc2:
            ser_pick = st.selectbox("Series", list(series_map.keys()), key="log_new_ser")
        series_id_new = series_map.get(ser_pick)

    ref_file = st.file_uploader(
        "Reference image", type=["jpg", "jpeg", "png"], key="log_ref_up",
        help="Stays on screen during your session. Not saved to the session log."
    )

    st.markdown("")
    start = st.button("▶ Start session")

    if start:
        if adding_new:
            if not new_title.strip():
                st.error("Please enter a painting title.")
                st.stop()
            conn.execute(
                "INSERT INTO paintings (title, status, series_id) VALUES (?, 'In progress', ?)",
                (new_title.strip(), series_id_new)
            )
            conn.commit()
            pid = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
            ptitle = new_title.strip()
            pseries = ser_pick if ser_pick != "— No series —" else None
        else:
            row = next(p for p in paintings if p["title"] == chosen)
            pid, ptitle, pseries = row["id"], row["title"], row["sn"]

        now = datetime.now()
        conn.execute(
            "INSERT INTO sessions (painting_id, date, start_time, is_draft) VALUES (?,?,?,1)",
            (pid, str(date.today()), now.strftime("%H:%M:%S"))
        )
        conn.commit()
        draft_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

        st.session_state.log_draft_id = draft_id
        st.session_state.log_start_time = now.strftime("%H:%M:%S")
        st.session_state.log_painting_id = pid
        st.session_state.log_painting_title = ptitle
        st.session_state.log_painting_series = pseries
        st.session_state.log_reference_image = ref_file.read() if ref_file else None
        st.session_state.log_phase = "active"
        st.rerun()


# ══════════════════════════════════════════════════════════════
# PHASE 2 — ACTIVE SESSION
# ══════════════════════════════════════════════════════════════
elif st.session_state.log_phase == "active":

    ptitle = st.session_state.log_painting_title
    pseries = st.session_state.log_painting_series
    series_str = f" — {pseries}" if pseries else ""

    # Auto-refresh every 60 seconds
    if AUTOREFRESH_AVAILABLE:
        st_autorefresh(interval=60000, key="log_timer_refresh")

    # Timer bar
    try:
        start_dt = datetime.combine(date.today(), datetime.strptime(st.session_state.log_start_time, "%H:%M:%S").time())
        mins_elapsed = max(0, int((datetime.now() - start_dt).total_seconds() / 60))
        h, m = divmod(mins_elapsed, 60)
        elapsed_display = f"{h}h {m}m" if h else f"{m}m"
    except Exception:
        elapsed_display = "—"

    st.markdown(f"🟢 &nbsp;**Session in progress** &nbsp;·&nbsp; {ptitle}{series_str}")
    st.markdown(f"### ⏱ {elapsed_display}")

    st.markdown("---")

    # Reference image + color finder
    ref_data = st.session_state.log_reference_image

    if ref_data is None:
        re_up = st.file_uploader(
            "Upload reference image", type=["jpg", "jpeg", "png"], key="log_ref_reup",
            help="Reference images are not persisted across refreshes. Upload to use the color finder."
        )
        if re_up:
            st.session_state.log_reference_image = re_up.read()
            st.rerun()
        st.info("No reference image loaded. You can continue without one, or upload one above.")
    else:
        img = Image.open(BytesIO(ref_data)).convert("RGB")
        max_w = 1400
        if img.width > max_w:
            img = img.resize((max_w, int(img.height * max_w / img.width)))

        my_paints = conn.execute("SELECT * FROM paints ORDER BY brand, name").fetchall()

        if IMAGE_COORDS_AVAILABLE:
            st.markdown("**Click on the image to identify a color:**")
            coords = streamlit_image_coordinates(img, key="log_cf_coords")
        else:
            st.image(img, use_container_width=True)
            coords = None
            st.warning("Install streamlit-image-coordinates for color picking: `pip install streamlit-image-coordinates`")

        if coords:
            x = min(coords["x"], img.width - 1)
            y = min(coords["y"], img.height - 1)
            r, g, b = img.getpixel((x, y))[:3]
            target_hex = rgb_to_hex(r, g, b)

            st.markdown("---")

            max_colors = st.slider("Maximum paints to mix", 1, 5, 3, key="log_cf_max_colors")

            # Pre-calculate mix
            mix_result, mix_hex = None, None
            if my_paints:
                with st.spinner("Calculating mix..."):
                    mix_result, _ = find_mix(target_hex, [dict(p) for p in my_paints], max_colors=max_colors)
                if mix_result:
                    mix_hex = mix_km_to_hex(
                        [p["hex_color"] for p, _ in mix_result],
                        [w for _, w in mix_result]
                    )

            # Row 1: target swatch | mix result swatch | mix recipe
            rc1, rc2, rc3 = st.columns([1, 1, 3])

            with rc1:
                st.markdown(
                    f'<div style="font-size:11px;color:gray;margin-bottom:3px;">Target</div>'
                    f'<div style="background:{target_hex};width:56px;height:56px;'
                    f'border-radius:8px;border:1px solid #ccc"></div>',
                    unsafe_allow_html=True
                )
                st.caption(f"`{target_hex.upper()}`")

            with rc2:
                if mix_hex:
                    st.markdown(
                        f'<div style="font-size:11px;color:gray;margin-bottom:3px;">Mix result</div>'
                        f'<div style="background:{mix_hex};width:56px;height:56px;'
                        f'border-radius:8px;border:1px solid #ccc"></div>',
                        unsafe_allow_html=True
                    )
                    st.caption(f"`{mix_hex.upper()}`")
                else:
                    st.caption("No mix result")

            with rc3:
                st.markdown("**Mix from your palette**")
                if my_paints:
                    if mix_result:
                        for paint, weight in mix_result:
                            st.markdown(
                                f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:5px">'
                                f'<div style="background:{paint["hex_color"]};width:20px;height:20px;'
                                f'border-radius:3px;border:1px solid #ccc;flex-shrink:0"></div>'
                                f'<span style="font-size:13px"><b>{weight}%</b> {paint["name"]}</span></div>',
                                unsafe_allow_html=True
                            )
                    else:
                        st.caption("Could not compute a mix.")
                else:
                    st.caption("Add paints to your collection for mix suggestions.")

            # Row 2: closest paints from database
            st.markdown("**Closest paints from database**")
            matches = find_best_matches(target_hex, all_paints_flat, top_n=5)
            for _, paint in matches:
                hv = paint["hex_color"]
                in_col = any(
                    p["name"] == paint["name"] and p["brand"] == paint.get("brand")
                    for p in my_paints
                )
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:5px">'
                    f'<div style="background:{hv};width:20px;height:20px;border-radius:3px;'
                    f'border:1px solid #ccc;flex-shrink:0"></div>'
                    f'<span style="font-size:13px">{paint["name"]} — {paint.get("brand","")}'
                    f'{"&nbsp;✅" if in_col else ""}</span></div>',
                    unsafe_allow_html=True
                )

    st.markdown("---")
    end_clicked = st.button("■ End session")

    if end_clicked:
        end_time = datetime.now().strftime("%H:%M:%S")
        dur = duration_mins(st.session_state.log_start_time, end_time)
        conn.execute(
            "UPDATE sessions SET end_time=?, duration_minutes=? WHERE id=?",
            (end_time, dur, st.session_state.log_draft_id)
        )
        conn.commit()
        st.session_state.log_end_time = end_time
        st.session_state.log_phase = "wrapup"
        st.rerun()


# ══════════════════════════════════════════════════════════════
# PHASE 3 — WRAP UP
# ══════════════════════════════════════════════════════════════
elif st.session_state.log_phase == "wrapup":

    ptitle = st.session_state.log_painting_title
    pseries = st.session_state.log_painting_series
    start_t = st.session_state.log_start_time
    end_t = st.session_state.log_end_time
    mins = duration_mins(start_t, end_t)
    series_str = f" — {pseries}" if pseries else ""

    st.success(
        f"**{ptitle}**{series_str} &nbsp;·&nbsp; {str(date.today())} "
        f"&nbsp;·&nbsp; Duration: **{dur_label(mins)}** "
        f"&nbsp;·&nbsp; {start_t[:5]} → {end_t[:5]}"
    )

    # Discard confirmation (shown above the form, blocks it)
    if st.session_state.get("log_discard_confirm"):
        st.error("Are you sure you want to discard this session? This cannot be undone.")
        dc1, dc2, _ = st.columns([1, 1, 3])
        with dc1:
            if st.button("Yes, discard", type="secondary"):
                conn.execute("DELETE FROM sessions WHERE id=?", (st.session_state.log_draft_id,))
                conn.commit()
                reset_session_state()
                st.rerun()
        with dc2:
            if st.button("Cancel"):
                st.session_state.log_discard_confirm = False
                st.rerun()
        st.stop()

    with st.form("log_wrapup_form"):

        c1, c2, c3 = st.columns(3)
        with c1:
            location = st.selectbox("Location", [""] + LOCATIONS)
        with c2:
            lighting = st.selectbox("Lighting", [""] + LIGHTING)
        with c3:
            mental_state = st.selectbox("Mental / physical state", [""] + MENTAL_STATES)

        c1, c2 = st.columns(2)
        with c1:
            techniques = st.multiselect("Techniques used", TECHNIQUES)
        with c2:
            brushes = st.multiselect("Brushes used", BRUSH_SIZES)

        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            rating = st.slider("Session rating", 1, 5, 3)
        with c2:
            completion = st.slider("Completion %", 0, 100, 0, step=1)

        st.markdown("---")

        what_worked_on = st.text_area("What I worked on")

        c1, c2 = st.columns(2)
        with c1:
            what_worked = st.text_area("What worked")
        with c2:
            what_didnt = st.text_area("What didn't work")

        c1, c2 = st.columns(2)
        with c1:
            do_differently = st.text_area("Do differently next time")
        with c2:
            whats_next = st.text_area("What's next")

        notes = st.text_area("Free notes")
        image_file = st.file_uploader("Session photo", type=["jpg", "jpeg", "png"])

        st.markdown("---")
        discard_btn = st.form_submit_button("Discard session")
        save_btn = st.form_submit_button("💾 Save session")

    if save_btn:
        image_path = None
        if image_file:
            fname = f"{st.session_state.log_painting_id}_{date.today()}_{image_file.name}"
            image_path = os.path.join(IMAGES_DIR, fname)
            with open(image_path, "wb") as f:
                f.write(image_file.getbuffer())

        conn.execute("""
            UPDATE sessions SET
                end_time=?, duration_minutes=?, completion_percent=?,
                location=?, lighting=?, mental_state=?, techniques=?,
                brushes_used=?, what_worked_on=?, what_worked=?,
                what_didnt_work=?, do_differently=?, whats_next=?,
                rating=?, notes=?, image_path=?, is_draft=0
            WHERE id=?
        """, (
            end_t, mins, completion,
            location, lighting, mental_state,
            ", ".join(techniques), ", ".join(brushes),
            what_worked_on, what_worked, what_didnt,
            do_differently, whats_next,
            rating, notes, image_path,
            st.session_state.log_draft_id
        ))

        # If session marked 100% complete, update painting status and finish date
        if completion == 100:
            existing = conn.execute(
                "SELECT date_finished FROM paintings WHERE id=?",
                (st.session_state.log_painting_id,)
            ).fetchone()
            finish_date = existing["date_finished"] if existing and existing["date_finished"] else str(date.today())
            conn.execute(
                "UPDATE paintings SET status='Complete', date_finished=? WHERE id=?",
                (finish_date, st.session_state.log_painting_id)
            )

        conn.commit()
        reset_session_state()
        st.success(f"Session saved! {dur_label(mins)} on '{ptitle}'.")
        st.rerun()

    if discard_btn:
        st.session_state.log_discard_confirm = True
        st.rerun()

conn.close()
