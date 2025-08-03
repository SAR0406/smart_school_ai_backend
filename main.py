from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, time
import json

app = FastAPI()

# Allow all origins for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict to specific domains here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load timetable JSON once
with open("timetable.json", "r") as f:
    timetable = json.load(f)

# Define fixed school period timings
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


# Utility: Get current period based on time
def get_current_period(now):
    current_time = now.time()
    for p in period_times:
        if p["start"] <= current_time < p["end"]:
            return p["period"]
    return None


# Endpoint 1: Get timetable for a class and day
@app.get("/get_timetable")
def get_timetable(class_name: str = Query(..., alias="class"), day: str = Query(...)):
    day = day.upper()
    if class_name not in timetable:
        return {"error": "Class not found"}
    if day not in timetable[class_name]:
        return {"error": "Day not found"}
    return {
        "class": class_name,
        "day": day,
        "timetable": timetable[class_name][day]
    }


# Endpoint 2: Get current period and subject for a class
@app.get("/get_current_period")
def get_current_period_data(class_name: str = Query(..., alias="class")):
    now = datetime.now()
    current_day = now.strftime('%A').upper()
    current_time_str = now.strftime("%H:%M")
    current_period = get_current_period(now)

    if class_name not in timetable:
        return {"error": "Class not found"}

    if not current_period:
        return {
            "class": class_name,
            "day": current_day,
            "time": current_time_str,
            "period": None,
            "message": "No active class period right now"
        }

    # Special periods
    if current_period in ["LUNCH", "SHORT_BREAK"]:
        return {
            "class": class_name,
            "day": current_day,
            "time": current_time_str,
            "period": current_period,
            "message": f"It is {current_period.replace('_', ' ').title()} 🍱"
        }

    # Normal class period
    subject = timetable[class_name].get(current_day, {}).get(current_period, "No Class")

    return {
        "class": class_name,
        "day": current_day,
        "time": current_time_str,
        "period": current_period,
        "subject": subject
    }


# Endpoint 3: List all available classes
@app.get("/get_all_classes")
def get_all_classes():
    return {"classes": list(timetable.keys())}


# Endpoint 4: Get today's schedule for a class
@app.get("/get_day_schedule")
def get_day_schedule(class_name: str = Query(..., alias="class")):
    current_day = datetime.now().strftime('%A').upper()

    if class_name not in timetable:
        return {"error": "Class not found"}

    today_schedule = timetable[class_name].get(current_day)
    if not today_schedule:
        return {"class": class_name, "day": current_day, "message": "No schedule available"}

    return {
        "class": class_name,
        "day": current_day,
        "schedule": today_schedule
    }


# Endpoint 5: Get full week schedule for a class
@app.get("/get_full_week")
def get_full_week(class_name: str = Query(..., alias="class")):
    if class_name not in timetable:
        return {"error": "Class not found"}
    return {
        "class": class_name,
        "week_schedule": timetable[class_name]
    }
