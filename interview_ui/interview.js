/*************************************************
 * GOD-LEVEL AI INTERVIEW ENGINE – interview.js
 * FULLSCREEN + CAMERA + TAB LOCK + STT + TTS
 * ZERO BACKEND CHANGES
 *************************************************/
if (window.location.protocol !== "https:") {
  alert("Secure connection required");
}

console.log("✅ interview.js loaded");

window.addEventListener("unhandledrejection", (e) => {
  console.error("❌ Unhandled promise rejection:", e.reason);
});

const API_BASE = "https://ai-screening-wbb0.onrender.com";
const params = new URLSearchParams(window.location.search);
const token = params.get("token");
let candidateId = null;

if (!token) {
  alert("Invalid interview link");
  throw new Error("token missing");
}

let interviewCompleted = false;
let interviewPaused = false;
let fullscreenExitCount = 0;
let tabSwitchCount = 0;
let cameraFailureCount = 0;
let interviewPausedForFullscreen = false;
let lastQuestionText = null;

const MAX_FULLSCREEN_EXIT = 3;
const MAX_TAB_SWITCH = 3;
const MAX_CAMERA_FAIL = 3;

let interviewStarted = false;
let interviewStartTime = null;
let interviewDurationMs = null;
// Question counter for UI
let questionCount = 0;

function showStatus(message) {
  const startBtn = document.getElementById("startInterviewBtn");
  startBtn.innerText = message;
  startBtn.disabled = true;
}

function hardStopTTS(reason = "") {
  try {
    speechSynthesis.cancel();
    console.warn("🔴 TTS force-stopped", reason);
  } catch {}
}

async function validateInterviewToken() {
  const token = new URLSearchParams(window.location.search).get("token");

  if (!token) {
    alert("Invalid interview link");
    throw new Error("Token missing");
  }

  const res = await fetch(`${API_BASE}/ai-interview/validate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ token })
  });

  if (!res.ok) {
    const errorText = await res.text();
    console.error("Validation failed:", errorText);
    alert("Interview expired or invalid.");
    throw new Error("Validation failed");
  }

  const data = await res.json();
  console.log("VALIDATION RESPONSE:", data);
  candidateId = data.candidate_id;
  /*window.interviewEndsAt = new Date(data.ends_at);
  interviewStartTime = new Date();
  interviewDurationMs = window.interviewEndsAt - interviewStartTime;
  startGlobalTimer();*/
}

/* ================= AI STATE ================= */
let aiState = "idle";

function setState(state) {
  aiState = state;
  document.body.setAttribute("data-state", state);
  console.log("AI STATE →", state);

  // Update UI status indicators
  updateStatusUI(state);
}

function updateStatusUI(state) {
  const statusLabel = document.getElementById("statusLabel");
  const statusMain  = document.getElementById("statusMain");
  const statusSub   = document.getElementById("statusSub");

  const states = {
    idle:      { label: "Idle",       main: "Idle",      sub: "Waiting to begin" },
    thinking:  { label: "Thinking…",  main: "Thinking",  sub: "AI is preparing your question" },
    asking:    { label: "Asking",     main: "Asking",    sub: "Listen carefully to the question" },
    listening: { label: "Listening…", main: "Listening", sub: "Speak your answer clearly" },
    completed: { label: "Completed",  main: "Done!",     sub: "Interview completed successfully" }
  };

  const s = states[state] || states.idle;

  if (statusLabel) statusLabel.textContent = s.label;
  if (statusMain)  statusMain.textContent  = s.main;
  if (statusSub)   statusSub.textContent   = s.sub;
}

/* ================= DOM ================= */
const questionEl = document.getElementById("question");
const answerBox  = document.getElementById("answerBox");
const micBtn     = document.getElementById("micBtn");
const submitBtn  = document.getElementById("submitBtn");
const timerEl = document.getElementById("hiddenTimer");
const videoEl    = document.getElementById("camera");

console.log("📹 videoEl =", videoEl);

/* ================= FULLSCREEN ENFORCEMENT (DISABLED) ================= */
/*
function requestFullscreen() { ... }
document.addEventListener("fullscreenchange", () => { ... });
*/

/* ================= TAB SWITCH DETECTION (DISABLED) ================= */
/*
document.addEventListener("visibilitychange", () => { ... });
*/

/* ================= TIMER ================= */
const QUESTION_TIME = 60;
let timerInterval;
let timeLeft = QUESTION_TIME;

function startTimer() {
  clearInterval(timerInterval);
  timeLeft = QUESTION_TIME;

  // Sync all timer UIs
  syncTimerDisplay(timeLeft);
  updateTimerBar(timeLeft);

  timerInterval = setInterval(() => {
    if (interviewCompleted || interviewPaused) {
      clearInterval(timerInterval);
      return;
    }

    timeLeft--;
    syncTimerDisplay(timeLeft);
    updateTimerBar(timeLeft);

    if (timeLeft <= 0) {
      clearInterval(timerInterval);
      if (answerBox.value.trim()) {
        submitAnswer();
      } else {
        fetchQuestion("");
      }
    }
  }, 1000);
}

function syncTimerDisplay(t) {
  // Keep hidden #timer updated for any JS that reads it
  if (timerEl) timerEl.innerText = `⏱ ${t}s`;

  // Update header timer
  const headerTime = document.querySelector(".header-time");
  if (headerTime) headerTime.innerText = `⏱ ${t}s`;

}

function updateTimerBar(t) {
  const bar = document.getElementById("timerBar");
  if (!bar) return;
  const pct = (t / QUESTION_TIME) * 100;
  bar.style.width = pct + "%";

  if (t <= 15) {
    bar.style.background = "linear-gradient(90deg, #ff5c5c, #ff2f2f)";
  } else if (t <= 30) {
    bar.style.background = "linear-gradient(90deg, #ffa755, #ff7c55)";
  } else {
    bar.style.background = "linear-gradient(90deg, #7c9cff, #a78bfa)";
  }
}

function updateTimeProgress(pct) {
  const fill  = document.getElementById("progressFill");
  const glow  = document.getElementById("progressGlow");
  const pctEl = document.getElementById("progressPct");

  if (fill)  fill.style.width  = pct + "%";
  if (glow)  glow.style.width  = pct + "%";
  if (pctEl) pctEl.textContent = pct + "%";
}

let globalTimerInterval;

function startGlobalTimer() {
  clearInterval(globalTimerInterval);

  globalTimerInterval = setInterval(() => {

    if (!window.interviewEndsAt || interviewCompleted) {
      return;
    }

    const now = new Date().getTime();
    const end = window.interviewEndsAt.getTime();
    const remaining = end - now;

    if (remaining <= 0) {
      clearInterval(globalTimerInterval);
      updateTimeProgress(100);
      finishInterview(false);
      return;
    }

    const total = end - interviewStartTime.getTime();
    if (total <= 0) return;
    const elapsed = total - remaining;
    const pct = Math.min(Math.floor((elapsed / total) * 100), 100);
    updateTimeProgress(pct);

    const minutes = Math.floor(remaining / 60000);
    const seconds = Math.floor((remaining % 60000) / 1000);

    const sidebarTimer = document.getElementById("sidebarTimer");
    if (sidebarTimer) {
      sidebarTimer.textContent =
        `${String(minutes).padStart(2,"0")}:${String(seconds).padStart(2,"0")}`;
    }

    const headerTime = document.querySelector(".header-time");
    if (headerTime) {
      headerTime.innerText =
        `${String(minutes).padStart(2,"0")}:${String(seconds).padStart(2,"0")}`;
    }

  }, 1000);
}


/* ================= TTS ================= */
function speak(text, onDone) {
  if (interviewPaused || interviewCompleted) return;
  speechSynthesis.cancel();

  const u    = new SpeechSynthesisUtterance(text);
  u.rate     = 0.95;
  u.pitch    = 1;
  u.volume   = 1;
  u.onend    = () => {
    if (!interviewPaused && onDone) onDone();
  };

  speechSynthesis.speak(u);
}

/* ================= STT ================= */
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

if (!SpeechRecognition) {
  alert("Speech recognition not supported.");
}

const recognition          = new SpeechRecognition();
recognition.lang           = "en-US";
recognition.interimResults = false;

micBtn.onclick = () => {
  answerBox.value = "";
  setState("listening");
  recognition.start();
};

recognition.onresult = (e) => {
  answerBox.value = e.results[0][0].transcript;
};

recognition.onend = () => {
  setState("idle");
  answerBox.focus();
};

/* ================= CAMERA (DISABLED) ================= */
/*
async function initCamera() { ... }
*/

/* ================= FETCH QUESTION ================= */
async function fetchQuestion(answer = null) {
  if (interviewCompleted || interviewPaused) return;

  try {
    setState("thinking");
    showLoadingState();

    const res = await fetch(`${API_BASE}/ai-interview/next`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_id: candidateId, answer })
    });

    const data = await res.json();

    if (!data.question && !data.completed) {
      console.error("Invalid question response:", data);
      alert("Interview session error. Please refresh.");
      return;
    }

    if (data.completed) {
      clearInterval(timerInterval);
      speechSynthesis.cancel();

      await fetch(`${API_BASE}/ai-interview/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_id: candidateId })
      });

      finishInterview(false);
      return;
    }

    submitBtn.disabled   = false;
    submitBtn.innerHTML  = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span>Submit Answer</span>
    `;
    if (data.ends_at) {
      window.interviewEndsAt = new Date(data.ends_at);

    if (!interviewStartTime) {
      interviewStartTime = new Date();
    }

    startGlobalTimer();
  }
    showQuestion(data.question, true);

  } catch (e) {
    submitBtn.disabled   = false;
    submitBtn.innerHTML  = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span>Submit Answer</span>
    `;
    alert("Interview error. Refresh if needed.");
  }
}

/* ================= LOADING STATE UI ================= */
function showLoadingState() {
  const loadingEl = document.getElementById("questionLoading");
  const textEl    = document.getElementById("questionText");
  if (loadingEl) loadingEl.style.display = "flex";
  if (textEl)    textEl.style.display    = "none";
}

/* ================= DISPLAY QUESTION ================= */
function showQuestion(q, isFirst = false) {
  if (interviewCompleted) return;

  questionCount++;

  // Update question number badge
  const badge = document.getElementById("questionBadge");
  if (badge) badge.textContent = `Q ${questionCount}`;

 

  // Hide loading, show text
  const loadingEl = document.getElementById("questionLoading");
  const textEl    = document.getElementById("questionText");

  if (loadingEl) loadingEl.style.display = "none";
  if (textEl) {
    textEl.style.display  = "block";
    textEl.style.opacity  = "0";
    textEl.style.transform = "translateY(10px)";
    textEl.textContent    = q;

    // Animate in
    requestAnimationFrame(() => {
      textEl.style.transition  = "opacity 0.4s ease, transform 0.4s ease";
      textEl.style.opacity     = "1";
      textEl.style.transform   = "translateY(0)";
    });
  }

  // Keep the original #question element text for JS compatibility
  questionEl.setAttribute("data-question", q);

  answerBox.value      = "";
  submitBtn.disabled   = false;

  setState("asking");

  if (isFirst) {
    speak(q, () => {
      setTimeout(() => {
        if (!interviewCompleted && !interviewPaused) startTimer();
      }, 500);
    });
  } else {
    speak(q, () => {
      if (!interviewCompleted && !interviewPaused) startTimer();
    });
  }
}


/* ================= SUBMIT ================= */
submitBtn.onclick = submitAnswer;

function submitAnswer() {
  if (interviewCompleted) return;

  const answer = answerBox.value.trim();
  if (!answer) {
    alert("Please answer before submitting.");
    return;
  }

  submitBtn.disabled  = true;
  submitBtn.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style="animation: spin 1s linear infinite">
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="10"/>
    </svg>
    <span>Submitting…</span>
  `;

  clearInterval(timerInterval);
  speechSynthesis.cancel();

  // Reset timer bar
  const bar = document.getElementById("timerBar");
  if (bar) {
    bar.style.transition = "width 0.3s ease";
    bar.style.width      = "0%";
  }
  document.body.classList.remove("timer-critical");

  fetchQuestion(answer);
}

/* ================= FINISH ================= */
function finishInterview(force = false) {
  if (interviewCompleted) return;
  interviewCompleted = true;

  try { mlCamera?.stop(); } catch {}

  setState("completed");
  clearInterval(timerInterval);
  speechSynthesis.cancel();

  // Stop camera if exists
  const video = document.getElementById("camera");
  if (video && video.srcObject) {
    video.srcObject.getTracks().forEach(track => track.stop());
    video.srcObject = null;
  }

  // Update progress to 100%
  const fill  = document.getElementById("progressFill");
  const glow  = document.getElementById("progressGlow");
  const pctEl = document.getElementById("progressPct");
  if (fill)  fill.style.width  = "100%";
  if (glow)  glow.style.width  = "100%";
  if (pctEl) pctEl.textContent = "100%";

  // Update badge
  const badge = document.getElementById("questionBadge");
  if (badge) badge.textContent = force ? "Ended" : "Done ✓";

  // Show completion UI in question box
  const loadingEl = document.getElementById("questionLoading");
  const textEl    = document.getElementById("questionText");

  if (loadingEl) loadingEl.style.display = "none";
  if (textEl) {
    textEl.style.display = "none";
  }

  // Build completion screen
  const completionHTML = force
    ? `<div class="completion-screen">
         <div class="completion-icon" style="border-color:rgba(255,92,92,0.4);background:rgba(255,92,92,0.1);">❌</div>
         <div class="completion-title" style="color:var(--danger)">Interview Terminated</div>
         <div class="completion-sub">Your session has been ended. Please contact support if needed.</div>
       </div>`
    : `<div class="completion-screen">
         <div class="completion-icon">✅</div>
         <div class="completion-title">Interview Complete!</div>
         <div class="completion-sub">Excellent work! Your responses have been submitted for evaluation. You'll hear back soon.</div>
       </div>`;

  questionEl.innerHTML = completionHTML;

  // Hide answer section and controls
  const answerSection = document.querySelector(".answer-section");
  const controls      = document.querySelector(".controls");
  if (answerSection) answerSection.style.display = "none";
  if (controls) controls.style.display = "none";

  // Update timers
  const sidebarTimer = document.getElementById("sidebarTimer");
  if (sidebarTimer) sidebarTimer.textContent = "--";

  const headerTime = document.querySelector(".header-time");
  if (headerTime) headerTime.innerText = "⏱ Done";

  if (timerEl) timerEl.innerText = "";

  // Update timer bar to 0
  const bar = document.getElementById("timerBar");
  if (bar) bar.style.width = "0%";

  document.body.classList.remove("timer-critical");

  if (!force) {
    speak("Thank you. Your interview is complete. You did a great job!");
  }
}

/* ================= CSS SPIN KEYFRAME (injected) ================= */
const spinStyle = document.createElement("style");
spinStyle.textContent = `
  @keyframes spin {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  }
`;
document.head.appendChild(spinStyle);

/* ================= ML ANTI-CHEAT (DISABLED) ================= */
/*
...all anti-cheat code commented out as in original...
*/

/* ================= START INTERVIEW ================= */
window.addEventListener("DOMContentLoaded", () => {
  const startBtn = document.getElementById("startInterviewBtn");

  if (!startBtn) {
    console.error("❌ Start Interview button not found");
    return;
  }

  console.log("✅ Start Interview button ready");

  startBtn.addEventListener("click", async () => {
    if (interviewStarted) return;
    interviewStarted = true;

    startBtn.innerHTML = `
      <span class="start-btn-icon">⟳</span>
      <span>Starting…</span>
      <div class="start-btn-glow"></div>
    `;
    startBtn.disabled = true;

    try {
      await validateInterviewToken();
      document.getElementById("startScreen")?.remove();
      fetchQuestion();
    } catch (e) {
      console.error(e);
      interviewStarted  = false;
      startBtn.innerHTML = `
        <span class="start-btn-icon">▶</span>
        <span>Start Interview</span>
        <div class="start-btn-glow"></div>
      `;
      startBtn.disabled = false;
    }
  });
});
