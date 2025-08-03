from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import os

# Load .env variables
load_dotenv()

# Init OpenAI Client for NVIDIA's API
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

app = FastAPI(
    title="Smart School AI",
    description="An intelligent assistant for school-related queries using NVIDIA's AI models.",
    version="1.0.0"
)

# Enable CORS (You can restrict allowed origins here)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- Models ---
class ChatRequest(BaseModel):
    user_id: Optional[str] = "anonymous"
    prompt: str
    temperature: Optional[float] = 0.7


class SimplePromptRequest(BaseModel):
    term: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    query: Optional[str] = None
    question: Optional[str] = None


# --- In-memory Storage ---
chat_histories: Dict[str, List[Dict[str, str]]] = {}


# --- Utility Functions ---
def get_user_history(user_id: str) -> List[Dict[str, str]]:
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    return chat_histories[user_id]


def add_to_history(user_id: str, role: str, content: str):
    history = get_user_history(user_id)
    history.append({"role": role, "content": content})
    if len(history) > 10:
        history.pop(0)


async def generate_response(messages, temperature=0.6, max_tokens=1024):
    try:
        completion = client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1",
            messages=messages,
            temperature=temperature,
            top_p=0.95,
            max_tokens=max_tokens,
            stream=False
        )
        return completion.choices[0].message.content

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")


# --- Routes ---
@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    user_id = req.user_id or str(uuid4())
    add_to_history(user_id, "user", req.prompt)

    history = get_user_history(user_id)
    messages = [{"role": "system", "content": "You are a helpful school assistant AI."}] + history

    reply = await generate_response(messages, temperature=req.temperature, max_tokens=2048)
    add_to_history(user_id, "assistant", reply)

    return {
        "user_id": user_id,
        "response": reply,
        "history": history
    }


@app.post("/define")
async def define(req: SimplePromptRequest):
    if not req.term:
        raise HTTPException(status_code=400, detail="Term is required.")
    messages = [
        {"role": "system", "content": "You are a dictionary bot that explains terms simply."},
        {"role": "user", "content": f"Define in simple words: {req.term}"}
    ]
    reply = await generate_response(messages)
    return {"response": reply}


@app.post("/formula")
async def formula(req: SimplePromptRequest):
    if not req.subject or not req.topic:
        raise HTTPException(status_code=400, detail="Subject and topic are required.")
    messages = [
        {"role": "system", "content": "You are a helpful formula assistant."},
        {"role": "user", "content": f"Give the most important formula related to {req.topic} in {req.subject}, explained clearly."}
    ]
    reply = await generate_response(messages)
    return {"response": reply}


@app.post("/explain")
async def explain(req: SimplePromptRequest):
    if not req.query:
        raise HTTPException(status_code=400, detail="Query is required.")
    messages = [
        {"role": "system", "content": "You are a teacher who explains things simply."},
        {"role": "user", "content": f"Explain this clearly and in simple terms: {req.query}"}
    ]
    reply = await generate_response(messages)
    return {"response": reply}


@app.post("/subject-expert")
async def subject_expert(req: SimplePromptRequest):
    if not req.subject or not req.question:
        raise HTTPException(status_code=400, detail="Subject and question are required.")
    messages = [
        {"role": "system", "content": f"You are an expert in {req.subject}."},
        {"role": "user", "content": f"Answer this question accurately: {req.question}"}
    ]
    reply = await generate_response(messages)
    return {"response": reply}


@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# --- Error Handlers ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }


# --- Run with: uvicorn ai:app --reload ---
