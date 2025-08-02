from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Literal
import json, os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY")
)

app = FastAPI()

# ========== Models ==========
class AskRequest(BaseModel):
    role: Literal['student', 'teacher']
    query: str

class TimetableRequest(BaseModel):
    class_name: str
    period: str

class Notice(BaseModel):
    title: str
    message: str

# ========== Endpoints ==========

@app.post("/ask")
async def ask_ai(data: AskRequest):
    system_prompt = "You are a helpful AI for students. Keep your answers clear, concise, and educational."
    if data.role == "teacher":
        system_prompt = "You are a helpful AI assistant for school teachers. Provide suggestions for teaching, homework, and student support."

    completion = client.chat.completions.create(
        model=os.getenv("MODEL_NAME"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": data.query}
        ],
        temperature=0.6,
        max_tokens=1024
    )
    reply = completion.choices[0].message.content
    return {"reply": reply}

@app.get("/timetable")
async def get_timetable(class_name: str, period: str):
    with open("timetable.json") as f:
        data = json.load(f)
    return {"subject": data.get(class_name, {}).get(period, "No class scheduled.")}

@app.get("/notifications")
async def get_notifications():
    with open("notifications.json") as f:
        data = json.load(f)
    return {"notices": data}

@app.post("/admin/notifications")
async def post_notice(notice: Notice):
    try:
        with open("notifications.json") as f:
            notices = json.load(f)
    except FileNotFoundError:
        notices = []

    notices.insert(0, notice.dict())

    with open("notifications.json", "w") as f:
        json.dump(notices, f, indent=2)

    return {"status": "Notice posted successfully."}

@app.post("/admin/timetable")
async def update_timetable(request: Request):
    new_data = await request.json()
    with open("timetable.json", "w") as f:
        json.dump(new_data, f, indent=2)
    return {"status": "Timetable updated."}
