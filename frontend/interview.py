import streamlit as st
import requests
import time
import json
from streamlit.components.v1 import html

# =====================================================
# CONFIG
# =====================================================
BACKEND_URL = st.secrets.get("BACKEND_URL", "https://your-backend.onrender.com")
MAX_QUESTIONS = 5
THINK_TIME_SECONDS = 60

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Futuready • AI Interview",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================
# HIDE STREAMLIT UI
# =====================================================
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
html, body, [class*="css"] {
    background: radial-gradient(circle at top, #020617, #000);
    color: #e5e7eb;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# SESSION STATE
# =====================================================
for k, v in {
    "candidate_id": None,
    "question": None,
    "q_index": 0,
    "answer": "",
    "completed": False,
    "thinking_start": None,
    "tts_done": False,
}.items():
    st.session_state.setdefault(k, v)

# =====================================================
# GET CANDIDATE ID
# =====================================================
params = st.query_params
if "candidate_id" not in params:
    st.error("❌ Invalid interview link")
    st.stop()

st.session_state.candidate_id = params["candidate_id"]

# =====================================================
# GLOBAL STYLES (FUTURISTIC)
# =====================================================
st.markdown("""
<style>
.glass {
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(20px);
    border-radius: 24px;
    padding: 32px;
    box-shadow: 0 0 60px rgba(56,189,248,0.15);
}
.title {
    font-size: 3rem;
    font-weight: 800;
    text-align: center;
    background: linear-gradient(90deg,#38bdf8,#22d3ee);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.question {
    font-size: 1.6rem;
    font-weight: 600;
}
.timer {
    color: #38bdf8;
    font-size: 1.1rem;
}
.btn {
    border: none;
    padding: 14px 26px;
    border-radius: 14px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
}
.mic { background:#2563eb;color:white; }
.stop { background:#dc2626;color:white; }
.submit { background:#22c55e;color:black; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# CAMERA (LEFT PANEL)
# =====================================================
html("""
<div style="text-align:center">
<video id="cam" autoplay muted playsinline
 style="width:100%;max-width:420px;border-radius:20px;
 border:2px solid rgba(56,189,248,.5);
 box-shadow:0 0 40px rgba(56,189,248,.25)">
</video>
</div>

<script>
navigator.mediaDevices.getUserMedia({video:true})
.then(s=>document.getElementById("cam").srcObject=s);
</script>
""", height=360)

# =====================================================
# SPEECH ENGINE (TTS + STT)
# =====================================================
html("""
<script>
let rec;
function startSTT(){
  rec=new webkitSpeechRecognition();
  rec.lang='en-US';
  rec.continuous=true;
  rec.onresult=e=>{
    let t='';
    for(let i=e.resultIndex;i<e.results.length;i++){
      t+=e.results[i][0].transcript+' ';
    }
    window.parent.postMessage({type:'stt',text:t},'*');
  };
  rec.start();
}
function stopSTT(){ if(rec) rec.stop(); }

function speak(text){
  let u=new SpeechSynthesisUtterance(text);
  u.rate=0.95;
  u.onend=()=>window.parent.postMessage({type:'tts_done'},'*');
  speechSynthesis.speak(u);
}
</script>
""", height=0)

# =====================================================
# BACKEND CALL
# =====================================================
def next_question(answer=None):
    r = requests.post(
        f"{BACKEND_URL}/ai-interview/next",
        json={"candidate_id": st.session_state.candidate_id, "answer": answer},
        timeout=30
    )
    r.raise_for_status()
    return r.json()

# =====================================================
# LOAD FIRST QUESTION
# =====================================================
if st.session_state.question is None:
    d = next_question()
    if d.get("completed"):
        st.session_state.completed = True
    else:
        st.session_state.question = d["question"]
        st.session_state.q_index = d["current"]
        st.session_state.tts_done = False

# =====================================================
# HEADER
# =====================================================
st.markdown("<div class='title'>🎧 Futuready AI Interview</div>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#94a3b8'>You will hear each question. You have 1 minute to think.</p>", unsafe_allow_html=True)

if st.session_state.completed:
    st.success("✅ Interview completed. You may close this tab.")
    st.stop()

# =====================================================
# QUESTION CARD
# =====================================================
st.markdown(f"""
<div class="glass">
<div class="question">
Question {st.session_state.q_index} of {MAX_QUESTIONS}
</div><br>
{st.session_state.question}
</div>
""", unsafe_allow_html=True)

# Speak question ONCE
if not st.session_state.tts_done:
    html(f"<script>speak({json.dumps(st.session_state.question)})</script>", height=0)

# =====================================================
# LISTEN FOR JS EVENTS
# =====================================================
html("""
<script>
window.addEventListener("message",(e)=>{
 if(e.data.type==='stt'){
   const ta=window.parent.document.getElementById("ans");
   if(ta) ta.value+=e.data.text;
 }
 if(e.data.type==='tts_done'){
   window.parent.postMessage({type:'start_timer'},'*');
 }
});
</script>
""", height=0)

# =====================================================
# THINKING TIMER
# =====================================================
if st.session_state.thinking_start:
    elapsed=int(time.time()-st.session_state.thinking_start)
    remain=max(0,THINK_TIME_SECONDS-elapsed)
    st.markdown(f"<p class='timer'>🧠 Thinking time: {remain}s</p>", unsafe_allow_html=True)
    if remain==0:
        st.warning("⏱️ Thinking time over. Please answer.")
else:
    html("""
    <script>
    window.addEventListener("message",(e)=>{
      if(e.data.type==='start_timer'){
        window.location.search+=''; 
      }
    });
    </script>
    """, height=0)
    st.session_state.thinking_start=time.time()
    st.session_state.tts_done=True

# =====================================================
# ANSWER INPUT
# =====================================================
st.text_area(
    "Your Answer",
    key="ans",
    height=180,
    placeholder="Your spoken answer will appear here…"
)

# =====================================================
# CONTROLS
# =====================================================
c1,c2,c3=st.columns(3)

with c1:
    html("<button class='btn mic' onclick='startSTT()'>🎤 Speak</button>",height=60)
with c2:
    html("<button class='btn stop' onclick='stopSTT()'>⏹ Stop</button>",height=60)
with c3:
    if st.button("Submit ➜", key="submit"):
        a=st.session_state.ans.strip()
        if not a:
            st.warning("Answer required")
        else:
            d=next_question(a)
            if d.get("completed"):
                st.session_state.completed=True
            else:
                st.session_state.question=d["question"]
                st.session_state.q_index=d["current"]
                st.session_state.thinking_start=None
                st.session_state.tts_done=False
                st.session_state.ans=""
            st.rerun()
