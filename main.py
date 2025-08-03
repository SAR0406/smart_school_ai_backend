from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, time
from typing import Optional, List, Dict, Any
import json
import os

from ai import router as ai_router  # AI features

app = FastAPI(
    title="📚 Smart School AI Assistant",
    description="A backend to manage school timetables and AI support for students.",
    version="2.0.0"
)

# --- Enable CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include AI router ---
app.include_router(ai_router, prefix="/ai", tags=["AI Assistant"])

# --- Load timetable.json ---
TIMETABLE_FILE = "timetable.json"
if not os.path.exists(TIMETABLE_FILE):
    raise FileNotFoundError("Missing timetable.json")

with open(TIMETABLE_FILE, "r") as f:
    timetable: Dict[str, Any] = json.load(f)

# --- Helper models ---
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
    message: Optional[str] = None

class ClassList(BaseModel):
    classes: List[str]

# --- Helper functions ---
def get_today() -> str:
    return datetime.now().strftime("%A")

def get_current_subject(today_schedule: List[Dict[str, str]]) -> Optional[str]:
    now = datetime.now().time()
    for period in today_schedule:
        start = datetime.strptime(period["start_time"], "%H:%M").time()
        end = datetime.strptime(period["end_time"], "%H:%M").time()
        if start <= now < end:
            return period["subject"]
    return None

def get_next_subject(today_schedule: List[Dict[str, str]]) -> Optional[str]:
    now = datetime.now().time()
    for period in today_schedule:
        start = datetime.strptime(period["start_time"], "%H:%M").time()
        if now < start:
            return period["subject"]
    return None

# --- API Endpoints ---
@app.get("/status", tags=["Utility"])
def status():
    return {"status": "✅ Smart School API is live!"}

@app.get("/get_current_period", response_model=CurrentPeriodResponse, tags=["Timetable"])
def get_current_period(class_name: str = Query(..., alias="class")):
    today = get_today()

    if today.lower() == "sunday":
        return {
            "class_name": class_name,
            "day": today,
            "time": datetime.now().strftime("%H:%M"),
            "message": "📅 Today is Sunday! No school today."
        }

    if timetable["class"] != class_name:
        raise HTTPException(status_code=404, detail="Class not found")

    today_schedule = timetable["daily_schedule"].get(today)
    if not today_schedule:
        raise HTTPException(status_code=404, detail="No schedule for today.")

    current_subject = get_current_subject(today_schedule)
    if current_subject:
        return {
            "class_name": class_name,
            "day": today,
            "time": datetime.now().strftime("%H:%M"),
            "current_subject": current_subject,
            "message": f"🕒 Ongoing class: {current_subject}"
        }

    next_subject = get_next_subject(today_schedule)
    if next_subject:
        return {
            "class_name": class_name,
            "day": today,
            "time": datetime.now().strftime("%H:%M"),
            "message": f"⏭️ No current class. Next up: {next_subject}"
        }

    return {
        "class_name": class_name,
        "day": today,
        "time": datetime.now().strftime("%H:%M"),
        "message": "🏁 School may be over for today!"
    }

@app.get("/get_day_schedule", response_model=TimetableResponse, tags=["Timetable"])
def get_day_schedule(class_name: str = Query(..., alias="class")):
    today = get_today()

    if timetable["class"] != class_name:
        raise HTTPException(status_code=404, detail="Class not found")

    if today.lower() == "sunday":
        return {
            "class_name": class_name,
            "day": today,
            "timetable": [{"subject": "Holiday", "start_time": "-", "end_time": "-"}]
        }

    today_schedule = timetable["daily_schedule"].get(today)
    if not today_schedule:
        raise HTTPException(status_code=404, detail="No schedule for today.")

    return {
        "class_name": class_name,
        "day": today,
        "timetable": today_schedule
    }

@app.get("/get_full_week", tags=["Timetable"])
def get_full_week(class_name: str = Query(..., alias="class")):
    if timetable["class"] != class_name:
        raise HTTPException(status_code=404, detail="Class not found")

    week_schedule = timetable["daily_schedule"].copy()
    week_schedule["Sunday"] = [{"subject": "Holiday", "start_time": "-", "end_time": "-"}]

    return {
        "class_name": class_name,
        "week_schedule": week_schedule
    }

@app.get("/get_all_classes", response_model=ClassList, tags=["Timetable"])
def get_all_classes():
    return {"classes": [timetable["class"]]}
