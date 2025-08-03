from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, time
from typing import Optional, List, Dict, Any
import json
import os

# === Import AI Routes ===
from ai import router as ai_router

app = FastAPI(
    title="📚 Smart School AI Assistant",
    description="A powerful backend for managing class schedules and AI-powered assistance.",
    version="2.0.0"
)

# === CORS Settings ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Mount AI Router ===
app.include_router(ai_router)

# === Load Timetable JSON ===
TIMETABLE_FILE = "timetable.json"
if not os.path.exists(TIMETABLE_FILE):
    raise FileNotFoundError("❌ timetable.json not found!")

with open(TIMETABLE_FILE, "r") as f:
    timetable: Dict[str, Any] = json.load(f)

# === Pydantic Models ===
class PeriodInfo(BaseModel):
    subject: str
    start_time: str
    end_time: str

class TimetableResponse(BaseModel):
    class_name: str
    day: str
    timetable: List[PeriodInfo]

class CurrentPeriodResponse(BaseModel):
    class_name: str
    day: str
    time: str
    current_subject: Optional[str] = None
    next_subject: Optional[str] = None
    message: Optional[str] = None

class ClassList(BaseModel):
    classes: List[str]

class FullWeekSchedule(BaseModel):
    class_name: str
    week_schedule: Dict[str, List[PeriodInfo]]

# === Utilities ===
def get_today() -> str:
    return datetime.now().strftime("%A")

def get_current_time() -> time:
    return datetime.now().time()

def parse_time(time_str: str) -> time:
    return datetime.strptime(time_str, "%H:%M").time()

def get_class_schedule(class_name: str, day: str) -> List[Dict[str, str]]:
    if timetable.get("class", "").lower() != class_name.lower():
        raise HTTPException(status_code=404, detail="Class not found in timetable.")

    schedule = timetable["daily_schedule"].get(day)
    if not schedule:
        raise HTTPException(status_code=404, detail=f"No schedule found for {day}.")

    return schedule

def get_current_subject(schedule: List[Dict[str, str]]) -> Optional[str]:
    now = get_current_time()
    for period in schedule:
        start = parse_time(period["start_time"])
        end = parse_time(period["end_time"])
        if start <= now < end:
            return period["subject"]
    return None

def get_next_subject(schedule: List[Dict[str, str]]) -> Optional[str]:
    now = get_current_time()
    for period in schedule:
        start = parse_time(period["start_time"])
        if now < start:
            return period["subject"]
    return None

# === API Endpoints ===

@app.get("/status", tags=["Utility"])
def status():
    return {"status": "✅ Smart School Backend is Running!"}

@app.get("/get_current_period", response_model=CurrentPeriodResponse, tags=["Timetable"])
def get_current_period(class_name: str = Query(..., alias="class")):
    today = get_today()
    now_str = datetime.now().strftime("%H:%M")

    if today == "Sunday":
        return {
            "class_name": class_name,
            "day": today,
            "time": now_str,
            "message": "📅 It's Sunday! Enjoy your holiday 😊"
        }

    schedule = get_class_schedule(class_name, today)
    current_subject = get_current_subject(schedule)
    next_subject = get_next_subject(schedule)

    if current_subject:
        message = f"🟢 Current class: {current_subject}"
    elif next_subject:
        message = f"⏭️ No class now. Next: {next_subject}"
    else:
        message = "🏁 School might be over for the day."

    return {
        "class_name": class_name,
        "day": today,
        "time": now_str,
        "current_subject": current_subject,
        "next_subject": next_subject,
        "message": message
    }

@app.get("/get_day_schedule", response_model=TimetableResponse, tags=["Timetable"])
def get_today_schedule(class_name: str = Query(..., alias="class")):
    today = get_today()

    if today == "Sunday":
        return {
            "class_name": class_name,
            "day": today,
            "timetable": [{"subject": "Holiday", "start_time": "-", "end_time": "-"}]
        }

    schedule = get_class_schedule(class_name, today)
    return {
        "class_name": class_name,
        "day": today,
        "timetable": schedule
    }

@app.get("/get_day_schedule/{day}", response_model=TimetableResponse, tags=["Timetable"])
def get_schedule_by_day(day: str, class_name: str = Query(..., alias="class")):
    if day.capitalize() == "Sunday":
        return {
            "class_name": class_name,
            "day": "Sunday",
            "timetable": [{"subject": "Holiday", "start_time": "-", "end_time": "-"}]
        }

    schedule = get_class_schedule(class_name, day.capitalize())
    return {
        "class_name": class_name,
        "day": day.capitalize(),
        "timetable": schedule
    }

@app.get("/get_full_week", response_model=FullWeekSchedule, tags=["Timetable"])
def get_full_week(class_name: str = Query(..., alias="class")):
    if timetable.get("class", "").lower() != class_name.lower():
        raise HTTPException(status_code=404, detail="Class not found.")

    full_week = timetable["daily_schedule"].copy()
    full_week["Sunday"] = [{"subject": "Holiday", "start_time": "-", "end_time": "-"}]

    return {
        "class_name": class_name,
        "week_schedule": full_week
    }

@app.get("/get_all_classes", response_model=ClassList, tags=["Timetable"])
def get_all_classes():
    # In the future: load from multiple class JSONs or DB
    return {"classes": [timetable.get("class", "Unknown")]}

# --- Extended Features ---

@app.get("/get_subjects", tags=["Timetable"])
def get_subjects():
    subjects = set()
    for day, periods in timetable.get("daily_schedule", {}).items():
        for period in periods:
            subjects.add(period["subject"])
    return {"subjects": sorted(subjects)}


@app.get("/get_teacher_schedule", tags=["Timetable"])
def get_teacher_schedule(teacher_name: str = Query(...)):
    teacher_schedule = {}

    for day, periods in timetable.get("daily_schedule", {}).items():
        teacher_schedule[day] = []
        for period in periods:
            if period.get("teacher", "").lower() == teacher_name.lower():
                teacher_schedule[day].append(period)

    if all(len(p) == 0 for p in teacher_schedule.values()):
        raise HTTPException(status_code=404, detail="No schedule found for this teacher.")

    return {
        "teacher_name": teacher_name,
        "schedule": teacher_schedule
    }


@app.get("/search_periods_by_subject", tags=["Search"])
def search_by_subject(subject: str = Query(...)):
    results = []
    for day, periods in timetable.get("daily_schedule", {}).items():
        for period in periods:
            if subject.lower() in period["subject"].lower():
                results.append({
                    "day": day,
                    "subject": period["subject"],
                    "start_time": period["start_time"],
                    "end_time": period["end_time"]
                })

    if not results:
        raise HTTPException(status_code=404, detail="No periods found for this subject.")
    
    return {"subject": subject, "results": results}


@app.get("/is_class_over_today", tags=["Timetable"])
def is_class_over_today(class_name: str = Query(..., alias="class")):
    today = get_today()
    now = get_current_time()

    if today == "Sunday":
        return {"class_name": class_name, "status": "Holiday"}

    schedule = get_class_schedule(class_name, today)
    last_end = parse_time(schedule[-1]["end_time"])

    return {
        "class_name": class_name,
        "current_time": now.strftime("%H:%M"),
        "last_class_end_time": last_end.strftime("%H:%M"),
        "is_over": now > last_end
    }


@app.get("/get_next_class_time", tags=["Timetable"])
def get_next_class_time(class_name: str = Query(..., alias="class")):
    today = get_today()
    now = get_current_time()

    if today == "Sunday":
        return {"class_name": class_name, "next_class": None, "message": "📅 It's Sunday!"}

    schedule = get_class_schedule(class_name, today)

    for period in schedule:
        start = parse_time(period["start_time"])
        if now < start:
            return {
                "class_name": class_name,
                "next_subject": period["subject"],
                "start_time": start.strftime("%H:%M")
            }

    return {"class_name": class_name, "message": "✅ All classes for today are done."}
