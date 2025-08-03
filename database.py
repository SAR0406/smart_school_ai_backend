# database.py

import json
import os
from datetime import datetime, time

# ------------------------
# 📂 Load Timetable JSON
# ------------------------

BASE_DIR = os.path.dirname(__file__)
TIMETABLE_PATH = os.path.join(BASE_DIR, "timetable.json")

with open(TIMETABLE_PATH, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

class_name = raw_data.get("class")
daily_schedule = raw_data.get("daily_schedule", {})

BREAK_SUBJECTS = {"Lunch Break", "Short Break"}


# ------------------------
# 🕒 Helper
# ------------------------

def parse_time(tstr):
    return datetime.strptime(tstr, "%H:%M").time()


# ------------------------
# 📚 Core Query Functions
# ------------------------

def get_class_name():
    return class_name

def get_all_days():
    return list(daily_schedule.keys())

def get_day_timetable(day):
    return daily_schedule.get(day, [])

def get_day_teaching_periods(day):
    return [
        period for period in get_day_timetable(day)
        if period["subject"] not in BREAK_SUBJECTS
    ]

def get_first_teaching_period(day):
    periods = get_day_teaching_periods(day)
    return periods[0] if periods else None

def get_last_teaching_period(day):
    periods = get_day_teaching_periods(day)
    return periods[-1] if periods else None

def get_current_period(day, current_time: time):
    for period in get_day_timetable(day):
        start = parse_time(period["start_time"])
        end = parse_time(period["end_time"])
        if start <= current_time < end:
            return period
    return None

def get_next_period(day, current_time: time):
    for period in get_day_timetable(day):
        start = parse_time(period["start_time"])
        if start > current_time:
            return period
    return None

def get_period_by_subject(day, subject):
    for period in get_day_teaching_periods(day):
        if period["subject"].lower() == subject.lower():
            return period
    return None

def get_full_week_schedule():
    return daily_schedule
