from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, time
from typing import Optional, List, Dict
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
    allow_origins=["*"],  # Change to frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include AI router ---
app.include_router(ai_router, prefix="/ai", tags=["AI Assistant"])

# --- Load Timetable ---
TIMETABLE_FILE = "timetable.json"
if not os.path.exists(TIMETABLE_FILE):
    raise FileNotFoundError("Missing timetable.json")

with open(TIMETABLE_FILE, "r") as f:
    timetable: Dict[str, Dict[str, Dict[str, str]]] = json.load(f)

# --- Period Time Definitions ---
period_times = [
    {"period": "1st", "start": time(9, 20), "end": time(10, 0)},
    {"period": "2nd", "start": time(10, 0), "end": time(10, 40)},
    {"period": "3rd", "start": time(10, 40), "end": time(11, 20)},
    {"period": "LUNCH", "start": time(11, 20), "end": time(11, 40)},
    {"period": "4th", "start": time(11, 40), "end": time(12, 20)},
    {"period": "5th", "start": time(12, 20), "end": time(13, 0)},
    {"period": "SHORT_BREAK", "start": time(13, 0), "end": time(13, 10)},
    {"period": "6th", "start": time(13, 10), "end": time(13, 50)},
    {"period": "7th", "start": time(13, 50), "end": time(14, 30)},
]

# --- Response Models ---
class PeriodInfo(BaseModel):
    period: str
    start: str
    end: str

class TimetableResponse(BaseModel):
    class_name: str
    day: str
    timetable: Dict[str, str]

class CurrentPeriodResponse(BaseModel):
    class_name: str
    day: str
    time: str
    period: Optional[str]
    message: Optional[str]
    subject: Optional[str] = None

class ClassList(BaseModel):
    classes: List[str]

# --- Utility Functions ---
def get_current_period(now: datetime) -> Optional[str]:
    current_time = now.time()
    for p in period_times:
        if p["start"] <= current_time < p["end"]:
            return p["period"]
    return None

def get_next_period(now: datetime) -> Optional[str]:
    current_time = now.time()
    for p in period_times:
        if current_time < p["start"]:
            return p["period"]
    return None

def is_sunday() -> bool:
    return datetime.now().strftime('%A').upper() == "SUNDAY"

# --- Routes ---
@app.get("/status", tags=["Utility"])
def status_check():
    return {"status": "✅ Smart School Assistant API is live!"}

@app.get("/get_timetable", response_model=TimetableResponse, tags=["Timetable"])
def get_timetable(class_name: str = Query(..., alias="class"), day: str = Query(...)):
    day = day.upper()

    if class_name not in timetable:
        raise HTTPException(status_code=404, detail="Class not found")
    
    if day == "SUNDAY":
        return {
            "class_name": class_name,
            "day": day,
            "timetable": {"info": "It's Sunday! No classes today 💤"}
        }

    if day not in timetable[class_name]:
        raise HTTPException(status_code=404, detail="Day not found in timetable")

    return {
        "class_name": class_name,
        "day": day,
        "timetable": timetable[class_name][day]
    }

@app.get("/get_current_period", response_model=CurrentPeriodResponse, tags=["Timetable"])
def get_current_period_data(class_name: str = Query(..., alias="class")):
    now = datetime.now()
    current_day = now.strftime('%A').upper()
    current_time_str = now.strftime("%H:%M")

    if class_name not in timetable:
        raise HTTPException(status_code=404, detail="Class not found")

    if current_day == "SUNDAY":
        return {
            "class_name": class_name,
            "day": current_day,
            "time": current_time_str,
            "period": None,
            "message": "It's Sunday! No school today 💤"
        }

    current_period = get_current_period(now)

    if not current_period:
        next_period = get_next_period(now)
        return {
            "class_name": class_name,
            "day": current_day,
            "time": current_time_str,
            "period": None,
            "message": f"No current class. Next period: {next_period}" if next_period else "School might be over."
        }

    if current_period in ["LUNCH", "SHORT_BREAK"]:
        return {
            "class_name": class_name,
            "day": current_day,
            "time": current_time_str,
            "period": current_period,
            "message": f"It is {current_period.replace('_', ' ').title()} 🍱"
        }

    subject = timetable[class_name].get(current_day, {}).get(current_period, "Free Period")

    return {
        "class_name": class_name,
        "day": current_day,
        "time": current_time_str,
        "period": current_period,
        "subject": subject
    }

@app.get("/get_all_classes", response_model=ClassList, tags=["Timetable"])
def get_all_classes():
    return {"classes": list(timetable.keys())}

@app.get("/get_day_schedule", response_model=TimetableResponse, tags=["Timetable"])
def get_day_schedule(class_name: str = Query(..., alias="class")):
    current_day = datetime.now().strftime('%A').upper()

    if class_name not in timetable:
        raise HTTPException(status_code=404, detail="Class not found")

    if current_day == "SUNDAY":
        return {
            "class_name": class_name,
            "day": current_day,
            "timetable": {"info": "It's Sunday! No classes today 💤"}
        }

    today_schedule = timetable[class_name].get(current_day)
    if not today_schedule:
        raise HTTPException(status_code=404, detail="No schedule for today.")

    return {
        "class_name": class_name,
        "day": current_day,
        "timetable": today_schedule
    }

@app.get("/get_full_week", tags=["Timetable"])
def get_full_week(class_name: str = Query(..., alias="class")):
    if class_name not in timetable:
        raise HTTPException(status_code=404, detail="Class not found")

    week_schedule = timetable[class_name].copy()
    week_schedule["SUNDAY"] = {"info": "It's Sunday! No classes today 💤"}

    return {
        "class_name": class_name,
        "week_schedule": week_schedule
    }
