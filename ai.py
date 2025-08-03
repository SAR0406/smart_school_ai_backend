from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Generator
from dotenv import load_dotenv
from openai import OpenAI
import os
import re

# Local imports from database.py
from database import get_current_period, get_today_timetable, get_week_timetable

# Load environment variables
load_dotenv()

# NVIDIA OpenAI client
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

router = APIRouter(
    prefix="/ai",
    tags=["NVIDIA AI Assistant"]
)

# ============ MODELS ============

class PromptRequest(BaseModel):
    prompt: str
    max_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.95
    stream: bool = True

class AIResponse(BaseModel):
    response: str

class ImagePrompt(BaseModel):
    prompt: str
    n: int = 1
    size: str = "512x512"

class ImageResponse(BaseModel):
    image_urls: List[str]

# ============ INTENT DETECTION & ROUTING ============

def extract_class_name(prompt: str) -> str | None:
    match = re.search(r'class\s+(\d+[a-zA-Z]*)', prompt.lower())
    return match.group(1) if match else None

def detect_timetable_intent(prompt: str) -> str | None:
    prompt = prompt.lower()
    if "current period" in prompt:
        return "current"
    elif "today's timetable" in prompt or "today timetable" in prompt:
        return "today"
    elif "full week" in prompt or "week timetable" in prompt:
        return "week"
    return None

def handle_timetable_logic(prompt: str) -> str | None:
    class_name = extract_class_name(prompt)
    if not class_name:
        return "❌ Please specify the class name like 'class 8A' in your prompt."

    intent = detect_timetable_intent(prompt)

    if intent == "current":
        return get_current_period(class_name)
    elif intent == "today":
        return get_today_timetable(class_name)
    elif intent == "week":
        return get_week_timetable(class_name)
    return None

# ============ SMART CHAT ENDPOINT ============

@router.post("/chat", response_model=None)
async def chat_with_nvidia(request: PromptRequest):
    try:
        # 🧠 Check if the prompt matches timetable-related logic
        timetable_response = handle_timetable_logic(request.prompt)
        if timetable_response:
            return {"response": timetable_response}

        # Otherwise, use LLM to respond
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant trained to help with school questions and general tasks."},
            {"role": "user", "content": request.prompt}
        ]

        def stream_response() -> Generator[str, None, None]:
            try:
                completion = client.chat.completions.create(
                    model="nvidia/llama-3.1-nemotron-ultra-253b-v1",
                    messages=messages,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens,
                    stream=True,
                )
                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            except Exception as e:
                yield f"[ERROR] {str(e)}"

        if request.stream:
            return StreamingResponse(stream_response(), media_type="text/plain")

        # Non-streaming fallback
        result = ""
        for chunk in client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1",
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=True,
        ):
            if chunk.choices[0].delta.content:
                result += chunk.choices[0].delta.content

        return {"response": result.strip()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")

# ============ CODE GENERATOR ============

@router.post("/code", response_model=AIResponse)
async def generate_code(request: PromptRequest):
    try:
        messages = [
            {"role": "system", "content": "You are an expert code generator. Write clean, working code."},
            {"role": "user", "content": request.prompt}
        ]

        response = ""
        for chunk in client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1",
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=True
        ):
            if chunk.choices[0].delta.content:
                response += chunk.choices[0].delta.content

        return {"response": response.strip()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code Gen Error: {str(e)}")

# ============ IMAGE GENERATOR PLACEHOLDER ============

@router.post("/image", response_model=ImageResponse)
async def generate_image(request: ImagePrompt):
    try:
        # Replace with real image generation API if needed
        return {"image_urls": ["https://example.com/image_placeholder.png"] * request.n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image Generation Error: {str(e)}")
