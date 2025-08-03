from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from openai import OpenAI
import os
import uvicorn
from datetime import datetime, timedelta

# --- Configuration ---
API_KEY = os.getenv("NVIDIA_API_KEY")
MODEL = "nvidia/llama-3.1-nemotron-ultra-253b-v1"

client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=API_KEY)

# --- App Setup ---
app = FastAPI(
    title="School AI Assistant",
    description="An AI-powered learning assistant using FastAPI + NVIDIA/OpenAI",
    version="1.0.0"
)

# --- In-memory user history and rate limit ---
chat_histories: Dict[str, List[Dict[str, str]]] = {}
rate_limits: Dict[str, datetime] = {}

# --- Request Models ---
class ChatRequest(BaseModel):
    user_id: str
    prompt: str
    temperature: Optional[float] = 0.7

class DefinitionRequest(BaseModel):
    user_id: str
    term: str

class FormulaRequest(BaseModel):
    user_id: str
    subject: str
    topic: str

class ExplanationRequest(BaseModel):
    user_id: str
    query: str

class SubjectExpertRequest(BaseModel):
    user_id: str
    subject: str
    question: str

# --- Utils ---
def get_user_history(user_id: str) -> List[Dict[str, str]]:
    return chat_histories.setdefault(user_id, [])

def add_to_history(user_id: str, role: str, content: str):
    history = get_user_history(user_id)
    history.append({"role": role, "content": content})
    if len(history) > 15:
        history.pop(0)

def is_rate_limited(user_id: str, seconds: int = 2) -> bool:
    now = datetime.utcnow()
    if user_id in rate_limits and (now - rate_limits[user_id]).total_seconds() < seconds:
        return True
    rate_limits[user_id] = now
    return False

# --- Core AI Handler ---
async def get_ai_response(messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1024):
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=temperature,
            top_p=0.95,
            max_tokens=max_tokens,
            stream=False
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")

# --- Routes ---
@app.post("/chat")
async def chat(req: ChatRequest):
    if is_rate_limited(req.user_id):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

    history = get_user_history(req.user_id)
    history.append({"role": "user", "content": req.prompt})
    messages = [{"role": "system", "content": "You are a helpful school AI assistant."}] + history

    reply = await get_ai_response(messages, temperature=req.temperature, max_tokens=2048)
    add_to_history(req.user_id, "assistant", reply)

    return {"response": reply, "history": history}


@app.post("/define")
async def define(req: DefinitionRequest):
    prompt = f"Define in simple words: {req.term}"
    messages = [{"role": "system", "content": "You are a definition bot."},
                {"role": "user", "content": prompt}]
    reply = await get_ai_response(messages)
    return {"term": req.term, "definition": reply}


@app.post("/formula")
async def formula(req: FormulaRequest):
    prompt = f"Give the most important formula related to {req.topic} in {req.subject}, with clear explanation."
    messages = [{"role": "system", "content": "You are a formula expert for school students."},
                {"role": "user", "content": prompt}]
    reply = await get_ai_response(messages)
    return {"formula": reply}


@app.post("/explain")
async def explain(req: ExplanationRequest):
    prompt = f"Explain this clearly and in simple terms: {req.query}"
    messages = [{"role": "system", "content": "You are an explainer AI for school students."},
                {"role": "user", "content": prompt}]
    reply = await get_ai_response(messages)
    return {"explanation": reply}


@app.post("/subject-expert")
async def subject_expert(req: SubjectExpertRequest):
    prompt = f"As a {req.subject} expert, answer this: {req.question}"
    messages = [{"role": "system", "content": f"You are a {req.subject} teacher AI."},
                {"role": "user", "content": prompt}]
    reply = await get_ai_response(messages)
    return {"subject": req.subject, "question": req.question, "answer": reply}


# --- Error Handler ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


# --- Run App ---
if __name__ == "__main__":
    uvicorn.run("ai:app", host="0.0.0.0", port=5001, reload=True)
