from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Generator
from dotenv import load_dotenv
from openai import OpenAI
import os
import sqlite3
from datetime import datetime
import pytz

# Load environment variables from .env
load_dotenv()

# Initialize NVIDIA-compatible OpenAI client
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

# ============ UTILITIES ============

def get_current_period(class_name: str):
    conn = sqlite3.connect("timetable.db")
    cursor = conn.cursor()

    # Get current time and day
    india_time = datetime.now(pytz.timezone("Asia/Kolkata"))
    current_day = india_time.strftime("%A")
    current_time = india_time.strftime("%H:%M")

    cursor.execute("""
        SELECT subject FROM timetable
        WHERE class = ? AND day = ? AND start_time <= ? AND end_time >= ?
    """, (class_name, current_day, current_time, current_time))

    result = cursor.fetchone()
    conn.close()

    if result:
        return f"The current period for class {class_name} is: 📚 {result[0]}"
    elif current_day.lower() == "sunday":
        return f"📅 Today is Sunday! No school today."
    else:
        return f"🔍 No ongoing period found right now for class {class_name} (Time: {current_time})"

# ============ AI CHAT ENDPOINT ============

@router.post("/chat", response_model=None)
async def chat_with_nvidia(request: PromptRequest):
    try:
        # Smart period integration
        if "current period" in request.prompt.lower() and "class" in request.prompt.lower():
            import re
            match = re.search(r"class\s+([0-9]+[a-zA-Z]*)", request.prompt)
            if match:
                class_name = match.group(1)
                return {"response": get_current_period(class_name)}

        messages = [
            {"role": "system", "content": "You are a smart assistant who also knows student timetables."},
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
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
            except Exception as e:
                yield f"[ERROR] {str(e)}"

        if request.stream:
            return StreamingResponse(stream_response(), media_type="text/plain")
        else:
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
            {"role": "system", "content": "You are a skilled programming assistant. Generate clean, efficient code."},
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

# ============ IMAGE GENERATOR STUB ============

@router.post("/image", response_model=ImageResponse)
async def generate_image(request: ImagePrompt):
    try:
        return {"image_urls": ["https://example.com/image_placeholder.png"] * request.n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image Generation Error: {str(e)}")
