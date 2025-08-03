from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Generator
from dotenv import load_dotenv
import os

from openai import OpenAI

# Load environment variables from .env
load_dotenv()

# Initialize NVIDIA-compatible OpenAI client
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")  # Rename to NVIDIA_API_KEY in your .env
)

# Create API router
router = APIRouter(
    prefix="/ai",
    tags=["NVIDIA AI Assistant"]
)

# =======================
# 🔷 Request/Response Models
# =======================

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

# =======================
# 🔷 Chat Completion Endpoint
# =======================

@router.post("/chat", response_model=None)
async def chat_with_nvidia(request: PromptRequest):
    try:
        # Prepare the messages format for LLM
        messages = [
            {"role": "system", "content": "You are a smart, creative, and detail-oriented assistant."},
            {"role": "user", "content": request.prompt}
        ]

        # Stream generator for real-time response
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
            # For non-streamed response
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

# =======================
# 🔷 Code Generator Endpoint
# =======================

@router.post("/code", response_model=AIResponse)
async def generate_code(request: PromptRequest):
    try:
        system_msg = "You are a highly skilled programming assistant. Generate well-documented and efficient code."
        messages = [
            {"role": "system", "content": system_msg},
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

# =======================
# 🧪 Future Expansion: Image Generator Stub
# =======================

@router.post("/image", response_model=ImageResponse)
async def generate_image(request: ImagePrompt):
    # NVIDIA API may not support DALL-E-like image generation yet
    # This is a stub — replace with actual image API when available
    try:
        return {"image_urls": ["https://example.com/image_placeholder.png"] * request.n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image Generation Error: {str(e)}")
