import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "painting_tracker.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            concept TEXT,
            target_paintings INTEGER,
            date_started TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paintings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'in progress',
            date_started TEXT,
            date_finished TEXT,
            paper_size TEXT,
            paper_type TEXT,
            genre TEXT,
            subject TEXT,
            style TEXT,
            mood TEXT,
            series_id INTEGER,
            inspiration_category TEXT,
            inspiration_note TEXT,
            FOREIGN KEY (series_id) REFERENCES series (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            painting_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            duration_minutes INTEGER,
            completion_percent INTEGER,
            location TEXT,
            lighting TEXT,
            reference_used TEXT,
            reference_detail TEXT,
            what_worked_on TEXT,
            whats_next TEXT,
            techniques TEXT,
            colors_used TEXT,
            brushes_used TEXT,
            mental_state TEXT,
            what_worked TEXT,
            what_didnt_work TEXT,
            do_differently TEXT,
            rating INTEGER,
            notes TEXT,
            image_path TEXT,
            FOREIGN KEY (painting_id) REFERENCES paintings (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            hex_color TEXT,
            brand TEXT
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_database()
    print("Database created successfully!")