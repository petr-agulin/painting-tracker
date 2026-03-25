import streamlit as st
from database import get_connection
import os
import base64
from datetime import datetime

st.set_page_config(page_title="Gallery", page_icon="🖼️", layout="wide")
st.title("🖼️ Gallery")
st.markdown("""
Your finished work, in one place. Images are added automatically when a session reaches 100% completion, or you can add them manually.
""")

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "images")

# ── One-time init: table + directory ─────────────────────────
@st.cache_resource
def init_gallery():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            painting_id INTEGER,
            session_id INTEGER,
            image_path TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            title TEXT,
            caption TEXT,
            date_added TEXT,
            FOREIGN KEY (painting_id) REFERENCES paintings(id),
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()
    os.makedirs(IMAGES_DIR, exist_ok=True)

init_gallery()

# ── Cached image encoder — keyed by path, refreshes on new version ──
@st.cache_data
def img_to_base64(path):
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext = path.split(".")[-1].lower()
        mime = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
        return f"data:{mime};base64,{data}"
    except Exception:
        return None

# ── Cached DB queries — version increments on any mutation ────
@st.cache_data
def fetch_entries(version):
    conn = get_connection()
    rows = conn.execute("""
        SELECT g.*, p.title as painting_title
        FROM gallery g
        LEFT JOIN paintings p ON p.id = g.painting_id
        WHERE g.image_path IS NOT NULL
        ORDER BY g.date_added DESC, g.id DESC
    """).fetchall()
    return [dict(r) for r in rows]

@st.cache_data
def fetch_entry(entry_id, version):
    conn = get_connection()
    row = conn.execute("""
        SELECT g.*, p.date_finished, p.status
        FROM gallery g
        LEFT JOIN paintings p ON p.id = g.painting_id
        WHERE g.id = ?
    """, (entry_id,)).fetchone()
    return dict(row) if row else None

def bump_version():
    st.session_state["gallery_version"] = st.session_state.get("gallery_version", 0) + 1

version = st.session_state.get("gallery_version", 0)

# ── Detail modal ──────────────────────────────────────────────
@st.dialog("Image details", width="large")
def gallery_detail(entry_id):
    entry = fetch_entry(entry_id, st.session_state.get("gallery_version", 0))
    if not entry:
        st.error("Not found.")
        return

    if entry["image_path"]:
        src = img_to_base64(entry["image_path"])
        if src:
            st.image(entry["image_path"], width=600)

    if entry["title"]:
        st.markdown(f"**{entry['title']}**")
    if entry["caption"]:
        st.markdown(entry["caption"])
    if entry["status"] == "Complete" and entry["date_finished"]:
        st.caption(f"Finished: {entry['date_finished']}")

    # ── Edit title ──
    if not st.session_state.get(f"editing_title_{entry_id}"):
        if st.button("Edit title", key=f"edit_title_btn_{entry_id}"):
            st.session_state[f"editing_title_{entry_id}"] = True

    if st.session_state.get(f"editing_title_{entry_id}"):
        with st.form(f"title_form_{entry_id}"):
            new_title = st.text_input("Title", value=entry["title"] or "")
            tc1, tc2 = st.columns([1, 1])
            with tc1:
                if st.form_submit_button("Save"):
                    conn = get_connection()
                    conn.execute("UPDATE gallery SET title=? WHERE id=?", (new_title, entry_id))
                    conn.commit()
                    st.session_state.pop(f"editing_title_{entry_id}", None)
                    bump_version()
                    st.rerun()
            with tc2:
                if st.form_submit_button("Cancel"):
                    st.session_state.pop(f"editing_title_{entry_id}", None)
                    st.rerun()

    # ── Edit caption ──
    if not st.session_state.get(f"editing_caption_{entry_id}"):
        if st.button("Edit caption", key=f"edit_cap_btn_{entry_id}"):
            st.session_state[f"editing_caption_{entry_id}"] = True

    if st.session_state.get(f"editing_caption_{entry_id}"):
        with st.form(f"caption_form_{entry_id}"):
            new_caption = st.text_area("Caption", value=entry["caption"] or "", height=80)
            cc1, cc2 = st.columns([1, 1])
            with cc1:
                if st.form_submit_button("Save"):
                    conn = get_connection()
                    conn.execute("UPDATE gallery SET caption=? WHERE id=?", (new_caption, entry_id))
                    conn.commit()
                    st.session_state.pop(f"editing_caption_{entry_id}", None)
                    bump_version()
                    st.rerun()
            with cc2:
                if st.form_submit_button("Cancel"):
                    st.session_state.pop(f"editing_caption_{entry_id}", None)
                    st.rerun()

    # ── Delete ──
    if not st.session_state.get(f"gal_confirm_delete_{entry_id}"):
        if st.button("Delete from Gallery", key=f"modal_delete_{entry_id}"):
            st.session_state[f"gal_confirm_delete_{entry_id}"] = True

    if st.session_state.get(f"gal_confirm_delete_{entry_id}"):
        st.error("Are you sure? This cannot be undone.")
        dc1, dc2 = st.columns([1, 1])
        with dc1:
            if st.button("Yes, delete", key=f"gal_yes_{entry_id}"):
                if entry["source"] == "manual" and os.path.exists(entry["image_path"]):
                    os.remove(entry["image_path"])
                    img_to_base64.clear()  # clear image cache for deleted file
                conn = get_connection()
                conn.execute("DELETE FROM gallery WHERE id=?", (entry_id,))
                conn.commit()
                st.session_state.pop(f"gal_confirm_delete_{entry_id}", None)
                st.session_state.pop("gallery_detail_id", None)
                st.session_state["gallery_dialog_open"] = False
                bump_version()
                st.rerun()
        with dc2:
            if st.button("Cancel", key=f"gal_cancel_{entry_id}"):
                st.session_state.pop(f"gal_confirm_delete_{entry_id}", None)
                st.rerun()

# ── Gallery grid ──────────────────────────────────────────────
entries = fetch_entries(version)

if st.button("Add image"):
    st.session_state["gallery_show_add"] = not st.session_state.get("gallery_show_add", False)
    st.session_state["gallery_dialog_open"] = False
    st.session_state.pop("gallery_detail_id", None)
    st.rerun()

if st.session_state.get("gallery_show_add"):
    upload = st.file_uploader("Image", type=["jpg", "jpeg", "png"], key="gallery_upload")
    add_title = st.text_input("Title (optional)", key="gallery_add_title")
    add_caption = st.text_input("Caption (optional)", key="gallery_add_caption")
    ac1, ac2 = st.columns([1, 1])
    with ac1:
        if st.button("Save", key="gallery_save_btn"):
            if not upload:
                st.error("Please upload an image.")
            else:
                fname = f"gallery_manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{upload.name}"
                fpath = os.path.join(IMAGES_DIR, fname)
                with open(fpath, "wb") as f:
                    f.write(upload.getbuffer())
                conn = get_connection()
                conn.execute(
                    "INSERT INTO gallery (image_path, source, title, caption, date_added) VALUES (?,?,?,?,?)",
                    (fpath, "manual", add_title or None, add_caption or None, str(datetime.today().date()))
                )
                conn.commit()
                st.session_state["gallery_show_add"] = False
                bump_version()
                st.rerun()
    with ac2:
        if st.button("Cancel", key="gallery_cancel_btn"):
            st.session_state["gallery_show_add"] = False
            st.rerun()

else:
    if not entries:
        st.info("No images in the gallery yet. Add one manually, or log a session at 100% completion with a photo.")
    else:
        st.markdown(f"**{len(entries)} image(s)**")
        st.markdown("---")

        COLS = 4
        for row_start in range(0, len(entries), COLS):
            row_entries = entries[row_start:row_start + COLS]
            cols = st.columns(COLS)
            for col, entry in zip(cols, row_entries):
                with col:
                    img_src = img_to_base64(entry["image_path"])
                    if img_src:
                        st.markdown(
                            f'<img src="{img_src}" style="width:100%;border-radius:6px;'
                            f'object-fit:cover;aspect-ratio:1/1;display:block;" />',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            '<div style="width:100%;aspect-ratio:1/1;background:#f0f0f0;border-radius:6px;'
                            'display:flex;align-items:center;justify-content:center;color:#aaa;font-size:12px">No image</div>',
                            unsafe_allow_html=True
                        )
                    if st.button("Full View", key=f"gal_open_{entry['id']}", use_container_width=True):
                        st.session_state["gallery_detail_id"] = entry["id"]
                        st.session_state["gallery_dialog_open"] = True
                        st.rerun()
                    label = entry["title"] or entry["painting_title"] or ""
                    if label:
                        st.caption(label)
                    if entry["caption"]:
                        st.caption(entry["caption"])

# ── Dialog trigger ────────────────────────────────────────────
if st.session_state.get("gallery_dialog_open") and "gallery_detail_id" in st.session_state:
    gallery_detail(st.session_state["gallery_detail_id"])
