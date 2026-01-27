import streamlit as st
import requests
import html

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")
QUESTION_TIME_SECONDS = 60

st.set_page_config(
    page_title="Futuready AI Interview",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ------------------ UI STYLE ------------------
st.markdown("""
<style>
body, .stApp {
    background: radial-gradient(circle at top, #0f2027, #000);
    color: #e8f1f8 !important;
}
.card {
    background: rgba(255,255,255,0.05);
    border-radius: 20px;
    padding: 28px;
    border: 1px solid rgba(0,255,255,0.25);
    box-shadow: 0 0 40px rgba(0,255,255,0.08);
}
button {
    border-radius: 12px !important;
    font-weight: 600 !important;
}
textarea {
    background: #050505 !important;
    color: #00ffd5 !important;
    border-radius: 14px !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------ PARAM CHECK ------------------
params = st.query_params
if "candidate_id" not in params:
    st.error("Invalid interview link")
    st.stop()

cid = params["candidate_id"]

# ------------------ LOAD QUESTION ------------------
if "question" not in st.session_state:
    r = requests.post(
        f"{BACKEND_URL}/ai-interview/next",
        json={"candidate_id": cid, "answer": None},
        timeout=60
    )
    d = r.json()
    st.session_state.question = d["question"]
    st.session_state.current = d["current"]
    st.session_state.total = d["total"]

safe_question = html.escape(st.session_state.question)

# ------------------ HEADER ------------------
st.markdown(f"""
<div class="card">
<h1>🎤 AI Interview</h1>
<p>Question {st.session_state.current} of {st.session_state.total}</p>
<div style="height:8px;border-radius:8px;
background:linear-gradient(90deg,#00ffd5,#007cf0);
width:{(st.session_state.current/st.session_state.total)*100}%"></div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------ INTERVIEW PANEL ------------------
st.components.v1.html(
    f"""
<div class="card">

<h3>Question</h3>
<p style="font-size:18px;">{safe_question}</p>

<video id="cam" autoplay muted playsinline
style="width:380px;border-radius:16px;
border:1px solid #00ffd5;margin-bottom:12px"></video>

<p id="timer" style="color:#ff7676;font-weight:bold;"></p>

<textarea id="ans" rows="5"
placeholder="Your spoken answer will appear here..."></textarea>

<br><br>
<button onclick="speak()">🔊 Listen</button>
<button onclick="startRec()">🎙 Start Answer</button>
<button onclick="stopRec()">⏹ Stop</button>

<button id="autoSubmit" style="display:none"></button>

<script>
let timeLeft = {QUESTION_TIME_SECONDS};
let timer;
let rec;

navigator.mediaDevices.getUserMedia({{video:true}})
.then(s => cam.srcObject = s)
.catch(() => console.log("Camera blocked"));

function speak() {{
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance("{safe_question}");
    u.rate = 0.95;
    speechSynthesis.speak(u);
}}

const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {{
    rec = new SpeechRecognition();
    rec.lang = "en-US";
    rec.continuous = true;
    rec.interimResults = true;

    rec.onresult = e => {{
        let text = "";
        for (let i = 0; i < e.results.length; i++) {{
            text += e.results[i][0].transcript + " ";
        }}
        document.getElementById("ans").value = text;
    }};
}}

function startRec() {{
    if (rec) rec.start();
}}

function stopRec() {{
    if (rec) rec.stop();
}}

function startTimer() {{
    timer = setInterval(() => {{
        timeLeft--;
        document.getElementById("timer").innerText =
            "⏱ Thinking time left: " + timeLeft + "s";
        if (timeLeft <= 0) {{
            clearInterval(timer);
            document.getElementById("autoSubmit").click();
        }}
    }}, 1000);
}}

window.onload = startTimer;
</script>

</div>
""",
    height=720
)

# ------------------ SUBMIT ------------------
answer = st.text_area("✍️ Edit answer if needed")

if st.button("🚀 Submit Answer") or st.session_state.get("auto", False):
    r = requests.post(
        f"{BACKEND_URL}/ai-interview/next",
        json={"candidate_id": cid, "answer": answer},
        timeout=90
    )
    d = r.json()

    if d.get("completed"):
        st.success("🎉 Interview completed")
        st.stop()

    st.session_state.question = d["question"]
    st.session_state.current = d["current"]
    st.rerun()
