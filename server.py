import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

from model import ask_question, conversation_history 

app = Flask(__name__)

conversation_history_sessions = {}  

MAX_HISTORY = 5

@app.route('/')
def index():
    session_id = request.cookies.get('session_id', str(os.getpid()))
    if session_id not in conversation_history_sessions:
        conversation_history_sessions[session_id] = []
    return render_template('index.html', session_id=session_id)


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_question = data.get('message')
    session_id = data.get('session_id')

    if not user_question or not session_id:
        return jsonify({"error": "Missing message or session ID"}), 400

    if session_id not in conversation_history_sessions:
        conversation_history_sessions[session_id] = []

    response_text = ask_question(user_question)

    history = conversation_history_sessions[session_id]
    history.append({"user": user_question, "bot": response_text})

    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    conversation_history_sessions[session_id] = history

    return jsonify({"response": response_text})

if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY"):
        print("🚨 GOOGLE_API_KEY not set!")
    else:
        print("🌍 Flask app starting on http://127.0.0.1:5000")
        app.run(debug=True, port=5000)
