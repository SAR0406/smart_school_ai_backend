from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, time
from typing import Optional, List, Dict, Any
import json
import os

from ai import router as ai_router  # Import AI assistant router

app = FastAPI(
    title="📚 Smart School AI Assistant",
    description="A powerful backend system for managing class timetables and AI support for students and teachers.",
    version="2.0.0"
)

# --- Enable CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include AI Router ---
app.include_router(ai_router, prefix="/ai", tags=["AI Assistant"])

# --- Load Timetable File ---
TIMETABLE_FILE = "timetable.json"
if not os.path.exists(TIMETABLE_FILE):
    raise FileNotFoundError("Missing timetable.json")

with open(TIMETABLE_FILE, "r") as f:
    timetable: Dict[str, Any] = json.load(f)

# --- Pydantic Models ---
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

# --- Helper Functions ---
def get_today() -> str:
    return datetime.now().strftime("%A")

def get_current_time() -> time:
    return datetime.now().time()

def parse_time(time_str: str) -> time:
    return datetime.strptime(time_str, "%H:%M").time()

def get_class_schedule(class_name: str, day: str) -> List[Dict[str, str]]:
    if timetable.get("class") != class_name:
        raise HTTPException(status_code=404, detail="Class not found")

    schedule = timetable["daily_schedule"].get(day)
    if not schedule:
        raise HTTPException(status_code=404, detail=f"No schedule available for {day}.")

    return schedule

def get_current_subject(schedule: List[Dict[str, str]]) -> Optional[str]:
    now = get_current_time()
    for period in schedule:
        if parse_time(period["start_time"]) <= now < parse_time(period["end_time"]):
            return period["subject"]
    return None

def get_next_subject(schedule: List[Dict[str, str]]) -> Optional[str]:
    now = get_current_time()
    for period in schedule:
        if now < parse_time(period["start_time"]):
            return period["subject"]
    return None

# --- API Endpoints ---
@app.get("/status", tags=["Utility"])
def status():
    return {"status": "✅ Smart School API is live!"}

@app.get("/get_current_period", response_model=CurrentPeriodResponse, tags=["Timetable"])
def get_current_period(class_name: str = Query(..., alias="class")):
    today = get_today()
    now_str = datetime.now().strftime("%H:%M")

    if today == "Sunday":
        return {
            "class_name": class_name,
            "day": today,
            "time": now_str,
            "message": "📅 It's Sunday! Enjoy your day off."
        }

    today_schedule = get_class_schedule(class_name, today)
    current_subject = get_current_subject(today_schedule)
    next_subject = get_next_subject(today_schedule)

    message = ""
    if current_subject:
        message = f"🕒 Ongoing class: {current_subject}"
    elif next_subject:
        message = f"⏭️ No class now. Next up: {next_subject}"
    else:
        message = "🏁 School day might be over."

    return {
        "class_name": class_name,
        "day": today,
        "time": now_str,
        "current_subject": current_subject,
        "next_subject": next_subject,
        "message": message
    }

@app.get("/get_day_schedule", response_model=TimetableResponse, tags=["Timetable"])
def get_day_schedule(class_name: str = Query(..., alias="class")):
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
def get_day_schedule_by_day(day: str, class_name: str = Query(..., alias="class")):
    schedule = get_class_schedule(class_name, day)
    return {
        "class_name": class_name,
        "day": day,
        "timetable": schedule
    }

@app.get("/get_full_week", response_model=FullWeekSchedule, tags=["Timetable"])
def get_full_week(class_name: str = Query(..., alias="class")):
    if timetable.get("class") != class_name:
        raise HTTPException(status_code=404, detail="Class not found")

    week_schedule = timetable["daily_schedule"].copy()
    week_schedule["Sunday"] = [{"subject": "Holiday", "start_time": "-", "end_time": "-"}]

    return {
        "class_name": class_name,
        "week_schedule": week_schedule
    }

@app.get("/get_all_classes", response_model=ClassList, tags=["Timetable"])
def get_all_classes():
    # Future enhancement: load multiple classes from DB or extended JSON
    return {"classes": [timetable.get("class", "Unknown")]}
