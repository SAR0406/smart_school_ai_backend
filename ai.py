from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import uvicorn
import os
import logging
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware

# --- App Initialization ---
app = FastAPI(
    title="School GPT Assistant",
    description="Smart school-focused assistant powered by NVIDIA/LLM APIs",
    version="1.0.0"
)

# --- Logging ---
logging.basicConfig(level=logging.INFO)

# --- CORS (if frontend exists) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- NVIDIA/OpenAI Client ---
def get_openai_client():
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.getenv("NVIDIA_API_KEY")
    )

# --- Models ---
class ChatInput(BaseModel):
    user_id: str
    prompt: str
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False


class SubjectInput(BaseModel):
    subject: str
    question: str


class ExplainInput(BaseModel):
    query: str


class DefineInput(BaseModel):
    term: str


class FormulaInput(BaseModel):
    subject: str
    topic: str


# --- In-Memory History ---
chat_histories: Dict[str, List[Dict[str, str]]] = {}
MAX_HISTORY = 10


def get_user_history(user_id: str) -> List[Dict[str, str]]:
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    return chat_histories[user_id]


def add_to_history(user_id: str, role: str, content: str):
    history = get_user_history(user_id)
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY:
        history.pop(0)


# --- Core Chat Function ---
def generate_completion(
    client: OpenAI,
    messages: List[Dict[str, str]],
    temperature: float,
    top_p: float,
    max_tokens: int,
    stream: bool = False
):
    try:
        completion = client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1",
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=stream
        )
        return completion
    except Exception as e:
        logging.error(f"Error during completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Routes ---

@app.post("/chat", tags=["Chat"])
def chat(input_data: ChatInput, client: OpenAI = Depends(get_openai_client)):
    user_id = input_data.user_id
    prompt = input_data.prompt
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing prompt")

    add_to_history(user_id, "user", prompt)
    history = get_user_history(user_id)
    messages = [{"role": "system", "content": "You are a helpful school assistant AI."}] + history

    completion = generate_completion(
        client=client,
        messages=messages,
        temperature=input_data.temperature,
        top_p=input_data.top_p,
        max_tokens=input_data.max_tokens,
        stream=input_data.stream
    )

    reply = completion.choices[0].message.content
    add_to_history(user_id, "assistant", reply)

    return {
        "response": reply,
        "history": history[-MAX_HISTORY:]
    }


@app.post("/define", tags=["Knowledge"])
def define_term(input_data: DefineInput, client: OpenAI = Depends(get_openai_client)):
    prompt = f"Define in simple words: {input_data.term}"
    return single_turn_chat(client, "definitions", prompt)


@app.post("/formula", tags=["Knowledge"])
def formula_lookup(input_data: FormulaInput, client: OpenAI = Depends(get_openai_client)):
    prompt = f"Give the most important formula related to {input_data.topic} in {input_data.subject}, explained clearly."
    return single_turn_chat(client, "formulas", prompt)


@app.post("/explain", tags=["Knowledge"])
def explain_concept(input_data: ExplainInput, client: OpenAI = Depends(get_openai_client)):
    prompt = f"Explain this clearly and in simple terms: {input_data.query}"
    return single_turn_chat(client, "explanation", prompt)


@app.post("/subject-expert", tags=["Subject Expert"])
def subject_expert_answer(input_data: SubjectInput, client: OpenAI = Depends(get_openai_client)):
    prompt = f"As a {input_data.subject} expert, answer the following question accurately: {input_data.question}"
    return single_turn_chat(client, input_data.subject, prompt)


# --- Helper Function ---
def single_turn_chat(client: OpenAI, context: str, prompt: str):
    messages = [
        {"role": "system", "content": f"You are a helpful AI assistant specialized in {context}."},
        {"role": "user", "content": prompt}
    ]

    completion = generate_completion(
        client=client,
        messages=messages,
        temperature=0.6,
        top_p=0.95,
        max_tokens=1024
    )

    reply = completion.choices[0].message.content
    return {"response": reply}


# --- Startup Info ---
@app.get("/", tags=["System"])
def root():
    return {
        "message": "Welcome to School GPT AI Assistant 🚀",
        "endpoints": ["/chat", "/define", "/formula", "/explain", "/subject-expert"]
    }


# --- Run with: uvicorn ai:app --reload ---
if __name__ == "__main__":
    uvicorn.run("ai:app", host="0.0.0.0", port=5001, reload=True)
