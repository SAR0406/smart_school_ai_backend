from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Generator, Optional
from dotenv import load_dotenv
from openai import OpenAI
import os
import sqlite3
from datetime import datetime
import pytz
import logging
import re

# ============ SETUP ============

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TIMEZONE = "Asia/Kolkata"
DATABASE = "timetable.db"
MODEL_ID = "nvidia/llama-3.1-nemotron-ultra-253b-v1"

# NVIDIA/OpenAI client
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

# ============ UTILITIES ============

def get_current_period(class_name: str) -> str:
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        india_time = datetime.now(pytz.timezone(TIMEZONE))
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
            return "📅 Today is Sunday! No school today."
        else:
            return f"🔍 No ongoing period found for class {class_name} at {current_time}."
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return "⚠️ Failed to fetch period info."

def build_messages(prompt: str, system_msg: str) -> List[dict]:
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ]

def extract_class_name(prompt: str) -> Optional[str]:
    match = re.search(r"class\s+([0-9]+[a-zA-Z]*)", prompt)
    return match.group(1) if match else None

# ============ ENDPOINT: CHAT ============

@router.post("/chat")
async def chat_with_nvidia(request: PromptRequest):
    try:
        # Smart timetable response
        if "current period" in request.prompt.lower() and "class" in request.prompt.lower():
            class_name = extract_class_name(request.prompt)
            if class_name:
                return {"response": get_current_period(class_name)}

        messages = build_messages(
            prompt=request.prompt,
            system_msg="You are a helpful assistant with access to school timetables and educational info."
        )

        def stream_response() -> Generator[str, None, None]:
            try:
                completion = client.chat.completions.create(
                    model=MODEL_ID,
                    messages=messages,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens,
                    stream=True
                )
                for chunk in completion:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            except Exception as e:
                logger.error(f"Streaming Error: {e}")
                yield f"[ERROR] {str(e)}"

        if request.stream:
            return StreamingResponse(stream_response(), media_type="text/plain")

        # Non-stream response
        response_text = ""
        for chunk in client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=True
        ):
            content = chunk.choices[0].delta.content
            if content:
                response_text += content

        return {"response": response_text.strip()}

    except Exception as e:
        logger.exception("AI Chat Error")
        raise HTTPException(status_code=500, detail=f"AI Chat Error: {str(e)}")

# ============ ENDPOINT: CODE GENERATION ============

@router.post("/code", response_model=AIResponse)
async def generate_code(request: PromptRequest):
    try:
        messages = build_messages(
            prompt=request.prompt,
            system_msg="You are a professional coding assistant. Write clean, documented code."
        )

        response_text = ""
        for chunk in client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=True
        ):
            content = chunk.choices[0].delta.content
            if content:
                response_text += content

        return {"response": response_text.strip()}

    except Exception as e:
        logger.exception("Code Generation Error")
        raise HTTPException(status_code=500, detail=f"Code Generation Error: {str(e)}")

# ============ ENDPOINT: DEFINE ============

@router.post("/define", response_model=AIResponse)
async def define_term(request: PromptRequest):
    try:
        messages = build_messages(
            prompt=f"Define this clearly: {request.prompt}",
            system_msg="You are an academic assistant. Define terms clearly and concisely."
        )

        response_text = ""
        for chunk in client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=True
        ):
            content = chunk.choices[0].delta.content
            if content:
                response_text += content

        return {"response": response_text.strip()}
    except Exception as e:
        logger.exception("Define Error")
        raise HTTPException(status_code=500, detail=f"Define Error: {str(e)}")






# ============ ENDPOINT: MY MODEL ============

@router.post("/myai", response_model=AIResponse)
async def define_term(request: PromptRequest):
    try:
        messages = build_messages(
            prompt=f"Define this clearly: {request.prompt}",
            system_msg="You are owned by Sarthak a 15 year old boy personal ai like jarvis . you are jarvis reply like you are jarvis or friday of iron man . reply with emoji and give your full inteliigence menation your user name who is sarthak and make him boss and reply him in boss and giver him selutation and respect act like jarvis and reply like jarvis and friday ."
        )

        response_text = ""
        for chunk in client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=True
        ):
            content = chunk.choices[0].delta.content
            if content:
                response_text += content

        return {"response": response_text.strip()}
    except Exception as e:
        logger.exception("Define Error")
        raise HTTPException(status_code=500, detail=f"Define Error: {str(e)}")
        

# ============ ENDPOINT: EXPLAIN ============

@router.post("/explain", response_model=AIResponse)
async def explain_concept(request: PromptRequest):
    try:
        messages = build_messages(
            prompt=f"Explain this like I'm 12 years old: {request.prompt}",
            system_msg="You are a teacher assistant. Explain complex topics in simple terms."
        )

        response_text = ""
        for chunk in client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=True
        ):
            content = chunk.choices[0].delta.content
            if content:
                response_text += content

        return {"response": response_text.strip()}
    except Exception as e:
        logger.exception("Explain Error")
        raise HTTPException(status_code=500, detail=f"Explain Error: {str(e)}")


# ============ ENDPOINT: QUIZ ============

@router.post("/quiz", response_model=AIResponse)
async def generate_quiz(request: PromptRequest):
    try:
        messages = build_messages(
            prompt=f"Create a short 5-question quiz on the topic: {request.prompt}",
            system_msg="You are a quiz generator bot for school subjects."
        )

        response_text = ""
        for chunk in client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=True
        ):
            content = chunk.choices[0].delta.content
            if content:
                response_text += content

        return {"response": response_text.strip()}
    except Exception as e:
        logger.exception("Quiz Generation Error")
        raise HTTPException(status_code=500, detail=f"Quiz Generation Error: {str(e)}")


# ============ ENDPOINT: SUMMARY ============

@router.post("/summary", response_model=AIResponse)
async def summarize_topic(request: PromptRequest):
    try:
        messages = build_messages(
            prompt=f"Summarize this clearly and briefly: {request.prompt}",
            system_msg="You are a summarization assistant. Keep it clear and short."
        )

        response_text = ""
        for chunk in client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=True
        ):
            content = chunk.choices[0].delta.content
            if content:
                response_text += content

        return {"response": response_text.strip()}
    except Exception as e:
        logger.exception("Summary Error")
        raise HTTPException(status_code=500, detail=f"Summary Error: {str(e)}")


# ============ ENDPOINT: FEEDBACK ============

@router.post("/feedback", response_model=AIResponse)
async def give_feedback(request: PromptRequest):
    try:
        messages = build_messages(
            prompt=f"Give constructive feedback on this work: {request.prompt}",
            system_msg="You are a school teacher assistant. Give fair and encouraging feedback."
        )

        response_text = ""
        for chunk in client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=True
        ):
            content = chunk.choices[0].delta.content
            if content:
                response_text += content

        return {"response": response_text.strip()}
    except Exception as e:
        logger.exception("Feedback Error")
        raise HTTPException(status_code=500, detail=f"Feedback Error: {str(e)}")


# ============ ENDPOINT: NOTES ============

@router.post("/notes", response_model=AIResponse)
async def generate_notes(request: PromptRequest):
    try:
        messages = build_messages(
            prompt=f"Generate short study notes on: {request.prompt}",
            system_msg="You are an educational note generator. Keep notes short and to the point."
        )

        response_text = ""
        for chunk in client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=True
        ):
            content = chunk.choices[0].delta.content
            if content:
                response_text += content

        return {"response": response_text.strip()}
    except Exception as e:
        logger.exception("Note Generation Error")
        raise HTTPException(status_code=500, detail=f"Note Generation Error: {str(e)}")
