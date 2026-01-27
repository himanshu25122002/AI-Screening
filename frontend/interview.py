import streamlit as st
import requests
import time
import json
from datetime import datetime
from streamlit.components.v1 import html

# =====================================================
# CONFIG
# =====================================================
BACKEND_URL = st.secrets.get("BACKEND_URL", "https://your-backend.onrender.com")
MAX_QUESTIONS = 5
THINK_TIME_SECONDS = 60

# =====================================================
# PAGE SETUP
# =====================================================
st.set_page_config(
    page_title="Futuready AI Interview",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide Streamlit chrome
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# SESSION STATE
# =====================================================
if "candidate_id" not in st.session_state:
    st.session_state.candidate_id = None
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "question_index" not in st.session_state:
    st.session_state.question_index = 0
if "answer" not in st.session_state:
    st.session_state.answer = ""
if "completed" not in st.session_state:
    st.session_state.completed = False
if "thinking_start" not in st.session_state:
    st.session_state.thinking_start = None

# =====================================================
# GET candidate_id
# =====================================================
params = st.query_params
if "candidate_id" not in params:
    st.error("Invalid interview link.")
    st.stop()

st.session_state.candidate_id = params["candidate_id"]

# =====================================================
# STYLES
# =====================================================
st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #0f172a, #020617);
    color: white;
}

.interview-card {
    background: rgba(255,255,255,0.06);
    border-radius: 20px;
    padding: 30px;
    box-shadow: 0 0 40px rgba(0,0,0,0.4);
}

.question-text {
    font-size: 1.6rem;
    font-weight: 600;
    margin-bottom: 20px;
}

.timer {
    font-size: 1.2rem;
    color: #38bdf8;
}

.mic-btn {
    background: #2563eb;
    color: white;
    border-radius: 50%;
    width: 90px;
    height: 90px;
    font-size: 2rem;
    border: none;
}

.stop-btn {
    background: #dc2626;
    color: white;
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 1rem;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# CAMERA COMPONENT
# =====================================================
html("""
<div style="text-align:center;">
<video id="video" autoplay muted playsinline
 style="width:100%;max-width:420px;border-radius:16px;border:2px solid #38bdf8;"></video>
</div>

<script>
navigator.mediaDevices.getUserMedia({ video: true })
.then(stream => {
  document.getElementById("video").srcObject = stream;
})
.catch(err => console.error(err));
</script>
""", height=300)

# =====================================================
# TTS + STT COMPONENT
# =====================================================
def speech_component():
    return html("""
<script>
let recognition;
let isListening = false;

function startListening() {
    if (!('webkitSpeechRecognition' in window)) {
        alert("Speech Recognition not supported");
        return;
    }

    recognition = new webkitSpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onresult = function(event) {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        window.parent.postMessage({ type: "answer", text: transcript }, "*");
    };

    recognition.start();
    isListening = true;
}

function stopListening() {
    if (recognition) {
        recognition.stop();
        isListening = false;
    }
}

function speak(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    speechSynthesis.speak(utterance);
}
</script>
""", height=0)

speech_component()

# =====================================================
# FETCH NEXT QUESTION
# =====================================================
def fetch_next_question(answer=None):
    payload = {
        "candidate_id": st.session_state.candidate_id,
        "answer": answer
    }
    r = requests.post(f"{BACKEND_URL}/ai-interview/next", json=payload)
    r.raise_for_status()
    return r.json()

# =====================================================
# INITIAL QUESTION
# =====================================================
if st.session_state.current_question is None:
    data = fetch_next_question()
    if data.get("completed"):
        st.session_state.completed = True
    else:
        st.session_state.current_question = data["question"]
        st.session_state.question_index = data["current"]
        st.session_state.thinking_start = time.time()

# =====================================================
# MAIN UI
# =====================================================
st.markdown("<h1 style='text-align:center;'>🎙️ Futuready AI Interview</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#94a3b8;'>Answer honestly. Take your time.</p>", unsafe_allow_html=True)

if st.session_state.completed:
    st.success("✅ Interview completed. Thank you for your time!")
    st.markdown("""
    <div class="interview-card">
        <h3>What happens next?</h3>
        <ul>
            <li>Your interview is being evaluated</li>
            <li>Our team will reach out if shortlisted</li>
            <li>No further action needed from you</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# =====================================================
# QUESTION CARD
# =====================================================
with st.container():
    st.markdown(f"""
    <div class="interview-card">
        <div class="question-text">
            Question {st.session_state.question_index} of {MAX_QUESTIONS}
        </div>
        <div class="question-text">
            {st.session_state.current_question}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Speak question
    html(f"""
    <script>
    speak({json.dumps(st.session_state.current_question)});
    </script>
    """, height=0)

# =====================================================
# THINKING TIMER
# =====================================================
elapsed = int(time.time() - st.session_state.thinking_start)
remaining = max(0, THINK_TIME_SECONDS - elapsed)

st.markdown(f"<p class='timer'>🧠 Thinking time: {remaining}s</p>", unsafe_allow_html=True)

if remaining > 0:
    time.sleep(1)
    st.rerun()

# =====================================================
# MIC CONTROLS
# =====================================================
st.markdown("### 🎤 Record your answer")

col1, col2 = st.columns([1, 1])

with col1:
    html("""
    <button class="mic-btn" onclick="startListening()">🎤</button>
    """, height=100)

with col2:
    html("""
    <button class="stop-btn" onclick="stopListening()">Stop</button>
    """, height=60)

# Receive answer
answer_box = st.empty()

html("""
<script>
window.addEventListener("message", (event) => {
    if (event.data.type === "answer") {
        const input = window.parent.document.getElementById("answer_input");
        if (input) {
            input.value += " " + event.data.text;
        }
    }
});
</script>
""", height=0)

st.text_area(
    "Your Answer",
    key="answer_input",
    height=150,
    placeholder="Your spoken answer will appear here..."
)

# =====================================================
# SUBMIT ANSWER
# =====================================================
if st.button("Submit Answer ➜"):
    answer = st.session_state.get("answer_input", "").strip()
    if not answer:
        st.warning("Please provide an answer.")
    else:
        data = fetch_next_question(answer)
        if data.get("completed"):
            st.session_state.completed = True
        else:
            st.session_state.current_question = data["question"]
            st.session_state.question_index = data["current"]
            st.session_state.thinking_start = time.time()
            st.session_state.answer_input = ""
        st.rerun()
