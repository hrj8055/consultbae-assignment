"""
Task 3: Mini audio collection app.

Two views (pick from the sidebar):
  - Submit: name + phone + audio upload -> extract features -> save to DB
  - View Submissions: list every submission with playback + stats

Run with: streamlit run app/audio_app.py   (from the project root)
"""

import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from audio_features import extract_audio_features
from normalize import normalize_phone, normalize_name

DB_PATH = "people.db"
UPLOAD_DIR = "app/audio_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def init_submissions_table():
    """Create the audio_submissions table if it doesn't exist yet.
    person_id links back to the SAME people table built in Stage 5 --
    this is what makes it one merged database instead of two islands."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audio_submissions (
            submission_id TEXT PRIMARY KEY,
            person_id INTEGER,
            name TEXT,
            phone TEXT,
            filepath TEXT,
            duration_sec REAL,
            sample_rate_hz INTEGER,
            bitrate_kbps REAL,
            loudness_db REAL,
            submitted_at TEXT
        )
    """)
    # Migration: if this table already existed from an earlier version
    # (before we added person_id), add the missing column now instead
    # of failing on every insert.
    existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(audio_submissions)")]
    if "person_id" not in existing_cols:
        conn.execute("ALTER TABLE audio_submissions ADD COLUMN person_id INTEGER")
    conn.commit()
    conn.close()


def find_or_create_person(name, phone):
    """
    Look up this person in the master people table (from Stage 5) by
    normalized phone. If found, return their existing person_id.
    If not found, create a new minimal person record so their data
    isn't orphaned, and return the new person_id.
    """
    norm_phone = normalize_phone(phone)
    norm_name = normalize_name(name)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    row = cur.execute(
        "SELECT person_id FROM people WHERE phone = ?", (norm_phone,)
    ).fetchone()

    if row:
        person_id = row[0]
    else:
        max_id_row = cur.execute("SELECT MAX(person_id) FROM people").fetchone()
        person_id = (max_id_row[0] or 0) + 1
        cur.execute(
            """INSERT INTO people
               (person_id, name, phone, source_naukri, source_gig, source_cbnexus)
               VALUES (?, ?, ?, 0, 0, 0)""",
            (person_id, norm_name, norm_phone),
        )
        conn.commit()

    conn.close()
    return person_id


def save_submission(person_id, name, phone, filepath, features):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO audio_submissions
           (submission_id, person_id, name, phone, filepath, duration_sec,
            sample_rate_hz, bitrate_kbps, loudness_db, submitted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            person_id,
            name,
            phone,
            filepath,
            features["duration_sec"],
            features["sample_rate_hz"],
            features["bitrate_kbps"],
            features["loudness_db"],
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_all_submissions():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT name, phone, filepath, duration_sec, sample_rate_hz, "
        "bitrate_kbps, loudness_db, submitted_at, person_id "
        "FROM audio_submissions ORDER BY submitted_at DESC"
    ).fetchall()
    conn.close()
    return rows


init_submissions_table()

st.title("Gig Worker Audio Submission")
page = st.sidebar.radio("View", ["Submit", "View Submissions"])

if page == "Submit":
    st.subheader("Submit a recording")

    name = st.text_input("Full name")
    phone = st.text_input("Phone number")

    st.write("Upload an audio file (or record one, if your browser supports it):")
    audio_file = st.file_uploader(
        "Audio file", type=["wav", "mp3", "m4a", "ogg", "webm"]
    )
    recorded_audio = None
    if hasattr(st, "audio_input"):
        recorded_audio = st.audio_input("Or record directly")

    source_audio = recorded_audio or audio_file

    if st.button("Submit"):
        if not name or not phone:
            st.error("Name and phone number are required.")
        elif not source_audio:
            st.error("Please upload or record an audio file.")
        else:
            ext = "wav" if recorded_audio else source_audio.name.split(".")[-1]
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(source_audio.getbuffer())

            try:
                features = extract_audio_features(filepath)
            except ValueError as e:
                st.error(f"Could not process audio: {e}")
                os.remove(filepath)
                st.stop()

            person_id = find_or_create_person(name, phone)
            save_submission(person_id, name, phone, filepath, features)

            st.success(f"Submission saved and linked to person_id {person_id}.")
            st.json(features)

elif page == "View Submissions":
    st.subheader("All submissions")
    rows = get_all_submissions()

    if not rows:
        st.info("No submissions yet.")
    else:
        for row in rows:
            (name, phone, filepath, duration, sample_rate,
             bitrate, loudness, submitted_at, person_id) = row
            with st.container(border=True):
                st.write(f"**{name}** — {phone}  ·  person_id: {person_id}")
                if os.path.exists(filepath):
                    st.audio(filepath)
                else:
                    st.warning("Audio file missing on disk.")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Duration", f"{duration}s")
                col2.metric("Sample rate", f"{sample_rate} Hz")
                col3.metric("Bitrate", f"{bitrate} kbps")
                col4.metric("Loudness", f"{loudness} dB")
                st.caption(f"Submitted: {submitted_at}")