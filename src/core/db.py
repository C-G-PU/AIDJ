import sqlite3
import os

class Database:
    def __init__(self, db_path="tracks.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    bpm REAL,
                    key_tag TEXT,
                    mood TEXT,
                    energy TEXT
                )
            ''')
            conn.commit()

    def add_track(self, file_path, title, bpm=None, key_tag=None, mood=None, energy=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tracks (file_path, title, bpm, key_tag, mood, energy)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    bpm=excluded.bpm,
                    key_tag=excluded.key_tag,
                    mood=excluded.mood,
                    energy=excluded.energy
            ''', (file_path, title, bpm, key_tag, mood, energy))
            conn.commit()
            return cursor.lastrowid

    def get_all_tracks(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tracks')
            return [dict(row) for row in cursor.fetchall()]

    def get_track_by_id(self, track_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tracks WHERE id = ?', (track_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
