import streamlit as st
import requests
import time
import json
from streamlit.components.v1 import html

# =========================
# CONFIG
# =========================
BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")
MAX_TIMEOUT = 90  # frontend safe timeout

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Futuready AI Interview",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================
# DARK FUTURISTIC UI
# =========================
st.markdown("""
<style>
html, body, [data-testid="stApp"] {
    background: radial-gradient(circle at top, #0f2027, #000000 60%);
    color: #e0e0e0;
    font-family: 'Inter', sans-serif;
}
h1, h2, h3 {
    color: #ffffff;
}
.glass {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(14px);
    border-radius: 18px;
    padding: 24px;
    box-shadow: 0 0 60px rgba(0,255,255,0.08);
}
.progress-bar {
    height: 8px;
    background: linear-gradient(90deg,#00ffd5,#007cf0);
    border-radius: 8px;
}
.timer {
    font-size: 18px;
    color: #00ffd5;
}
button {
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION INIT
# =========================
if "candidate_id" not in st.session_state:
    params = st.query_params
    if "candidate_id" not in params:
        st.error("❌ Invalid interview link.")
        st.stop()
    st.session_state.candidate_id = params["candidate_id"]

for key, val in {
    "question": None,
    "current": 0,
    "total": 5,
    "answer": "",
    "loading": False
}.items():
    st.session_state.setdefault(key, val)

# =========================
# BACKEND CALL (SAFE)
# =========================
def fetch_next_question(answer=None):
    try:
        r = requests.post(
            f"{BACKEND_URL}/ai-interview/next",
            json={
                "candidate_id": st.session_state.candidate_id,
                "answer": answer
            },
            timeout=MAX_TIMEOUT
        )
        r.raise_for_status()
        return r.json()

    except requests.exceptions.ReadTimeout:
        st.warning("🧠 AI is thinking deeply… please wait.")
        time.sleep(2)
        st.rerun()

    except Exception as e:
        st.error(f"❌ Interview error: {e}")
        st.stop()

# =========================
# INITIAL QUESTION
# =========================
if st.session_state.question is None:
    data = fetch_next_question()
    st.session_state.question = data["question"]
    st.session_state.current = data.get("current", 1)
    st.session_state.total = data.get("total", 5)

# =========================
# HEADER
# =========================
st.markdown(f"""
<div class="glass">
<h1>🎤 AI Interview</h1>
<p>Question {st.session_state.current} of {st.session_state.total}</p>
<div class="progress-bar" style="width:{(st.session_state.current/st.session_state.total)*100}%;"></div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =========================
# QUESTION + TTS + TIMER + CAMERA + STT
# =========================
html(f"""
<div class="glass">
<h3>Question</h3>
<p>{st.session_state.question}</p>

<div class="timer" id="timer">Thinking time: 60s</div>

<video id="camera" autoplay muted playsinline
       style="width:100%;max-width:420px;border-radius:14px;margin-top:16px;border:1px solid #00ffd5"></video>

<textarea id="transcript" placeholder="Your spoken answer will appear here..."
style="width:100%;height:140px;margin-top:16px;
background:#000;color:#0ff;border-radius:12px;padding:12px;"></textarea>

<div style="margin-top:12px;">
<button onclick="startListening()">🎙 Start Answer</button>
<button onclick="stopListening()">⏹ Stop</button>
<button onclick="speakQuestion()">🔊 Repeat Question</button>
</div>

<script>
let recognition;
let timeLeft = 60;

// CAMERA
navigator.mediaDevices.getUserMedia({{video:true,audio:false}})
.then(stream => {{
  document.getElementById("camera").srcObject = stream;
}});

// TIMER
setInterval(() => {{
  if(timeLeft > 0) {{
    timeLeft--;
    document.getElementById("timer").innerText = "Thinking time: " + timeLeft + "s";
  }}
}}, 1000);

// STT
function startListening() {{
  recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  recognition.lang = "en-US";
  recognition.continuous = true;
  recognition.onresult = (e) => {{
    document.getElementById("transcript").value += e.results[e.results.length-1][0].transcript + " ";
  }};
  recognition.start();
}}

function stopListening() {{
  if(recognition) recognition.stop();
}}

// TTS
function speakQuestion() {{
  let msg = new SpeechSynthesisUtterance("{st.session_state.question}");
  msg.rate = 0.95;
  msg.pitch = 1.1;
  speechSynthesis.speak(msg);
}}
</script>
</div>
""", height=700)

st.markdown("<br>", unsafe_allow_html=True)

# =========================
# ANSWER SUBMIT
# =========================
answer = st.text_area("✍️ Edit answer if needed", height=120)

col1, col2 = st.columns([1,1])

with col1:
    if st.button("🚀 Submit Answer"):
        st.session_state.loading = True
        data = fetch_next_question(answer)

        if data.get("completed"):
            st.success("✅ Interview completed. Thank you!")
            st.stop()

        st.session_state.question = data["question"]
        st.session_state.current = data["current"]
        st.session_state.answer = ""
        st.rerun()

with col2:
    if st.button("❌ Exit Interview"):
        st.warning("Interview exited.")
        st.stop()
