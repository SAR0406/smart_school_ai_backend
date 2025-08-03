import sqlite3
from datetime import datetime
import pytz
from typing import Optional, List, Tuple

DB_NAME = "timetable.db"

# ========== DATABASE SETUP ==========
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timetable (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class TEXT NOT NULL,
                day TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                subject TEXT NOT NULL
            )
        """)
        conn.commit()


# ========== INSERT ==========
def add_period(class_name: str, day: str, start_time: str, end_time: str, subject: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO timetable (class, day, start_time, end_time, subject)
            VALUES (?, ?, ?, ?, ?)
        """, (class_name, day.capitalize(), start_time, end_time, subject))
        conn.commit()


# ========== FETCH ==========
def get_timetable(class_name: str, day: Optional[str] = None) -> List[Tuple]:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if day:
            cursor.execute("""
                SELECT day, start_time, end_time, subject
                FROM timetable
                WHERE class = ? AND day = ?
                ORDER BY start_time
            """, (class_name, day.capitalize()))
        else:
            cursor.execute("""
                SELECT day, start_time, end_time, subject
                FROM timetable
                WHERE class = ?
                ORDER BY day, start_time
            """, (class_name,))
        return cursor.fetchall()


# ========== CURRENT PERIOD ==========
def get_current_period(class_name: str) -> str:
    india_time = datetime.now(pytz.timezone("Asia/Kolkata"))
    current_day = india_time.strftime("%A")
    current_time = india_time.strftime("%H:%M")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT subject FROM timetable
            WHERE class = ? AND day = ? AND start_time <= ? AND end_time >= ?
        """, (class_name, current_day, current_time, current_time))

        result = cursor.fetchone()

    if result:
        return f"🕒 Current period for class {class_name} is: {result[0]}"
    elif current_day.lower() == "sunday":
        return f"🎉 Sunday! No classes today."
    else:
        return f"📭 No ongoing class for {class_name} at {current_time}."


# ========== DELETE ==========
def delete_period_by_id(period_id: int) -> bool:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM timetable WHERE id = ?", (period_id,))
        return cursor.rowcount > 0


# ========== LIST CLASSES ==========
def list_classes() -> List[str]:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT class FROM timetable")
        return [row[0] for row in cursor.fetchall()]
