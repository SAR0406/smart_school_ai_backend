from flask import Flask, request, jsonify
from openai import OpenAI
from datetime import datetime
import os

app = Flask(__name__)

# NVIDIA/OpenAI Model API Configuration
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")  # Set this as environment variable
)

# Chat History Storage (simple, in-memory)
chat_histories = {}

# --- Utils ---
def get_user_history(user_id):
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    return chat_histories[user_id]

def add_to_history(user_id, role, content):
    history = get_user_history(user_id)
    history.append({"role": role, "content": content})
    # Keep only latest 10 interactions
    if len(history) > 10:
        history.pop(0)

# --- Routes ---

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_id = data.get("user_id", "anonymous")
    prompt = data.get("prompt")
    temperature = float(data.get("temperature", 0.7))

    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400

    add_to_history(user_id, "user", prompt)

    # Build chat messages with history
    history = get_user_history(user_id)
    messages = [{"role": "system", "content": "You are a helpful school assistant AI."}] + history

    try:
        completion = client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1",
            messages=messages,
            temperature=temperature,
            top_p=0.95,
            max_tokens=2048,
            stream=False
        )

        reply = completion.choices[0].message.content
        add_to_history(user_id, "assistant", reply)

        return jsonify({"response": reply, "history": history})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/define", methods=["POST"])
def get_definition():
    data = request.json
    term = data.get("term")
    if not term:
        return jsonify({"error": "Missing term"}), 400

    prompt = f"Define in simple words: {term}"
    return chat_with_prompt("definitions", prompt)


@app.route("/formula", methods=["POST"])
def get_formula():
    data = request.json
    subject = data.get("subject")
    topic = data.get("topic")
    if not subject or not topic:
        return jsonify({"error": "Missing subject or topic"}), 400

    prompt = f"Give the most important formula related to {topic} in {subject}, explained clearly."
    return chat_with_prompt("formulas", prompt)


@app.route("/explain", methods=["POST"])
def get_explanation():
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify({"error": "Missing query"}), 400

    prompt = f"Explain this clearly and in simple terms: {query}"
    return chat_with_prompt("explanation", prompt)


@app.route("/subject-expert", methods=["POST"])
def subject_expert():
    data = request.json
    subject = data.get("subject")
    question = data.get("question")
    if not subject or not question:
        return jsonify({"error": "Missing subject or question"}), 400

    prompt = f"As a {subject} expert, answer the following question accurately: {question}"
    return chat_with_prompt(subject.lower(), prompt)


# --- Core AI Calling Function ---
def chat_with_prompt(context, prompt):
    try:
        messages = [
            {"role": "system", "content": f"You are a helpful AI assistant specialized in {context}."},
            {"role": "user", "content": prompt}
        ]

        completion = client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1",
            messages=messages,
            temperature=0.6,
            top_p=0.95,
            max_tokens=1024,
            stream=False
        )

        reply = completion.choices[0].message.content
        return jsonify({"response": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Start Server ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)
