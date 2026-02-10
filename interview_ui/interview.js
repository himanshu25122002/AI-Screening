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

function hardStopTTS(reason = "") {
  try {
    speechSynthesis.cancel();
    console.warn("🛑 TTS force-stopped", reason);
  } catch {}
}


async function validateInterviewToken() {
  const token = new URLSearchParams(window.location.search).get("token");

  if (!token) {
    alert("Invalid interview link");
    return;
  }

  const res = await fetch(`${API_BASE}/ai-interview/validate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ token })   // 🔥 THIS LINE FIXES 422
  });

  if (!res.ok) {
    throw new Error("Interview validation failed");
  }

  const data = await res.json();
  candidateId = data.candidate_id;
}



/* ================= AI STATE ================= */
let aiState = "idle";
function setState(state) {
  aiState = state;
  document.body.setAttribute("data-state", state);
  console.log("AI STATE →", state);
}

/* ================= DOM ================= */
const questionEl = document.getElementById("question");
const answerBox = document.getElementById("answerBox");
const micBtn = document.getElementById("micBtn");
const submitBtn = document.getElementById("submitBtn");
const timerEl = document.getElementById("timer");
const videoEl = document.getElementById("camera");
console.log("🎥 videoEl =", videoEl);
/* ================= FULLSCREEN ENFORCEMENT ================= */
function requestFullscreen() {
  const el = document.documentElement;
  if (el.requestFullscreen) el.requestFullscreen();
  else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
}

function pauseInterviewForFullscreen() {
  if (interviewCompleted || interviewPaused) return;

  interviewPaused = true;
  interviewPausedForFullscreen = true;

  clearInterval(timerInterval);
  speechSynthesis.cancel();    

  const overlay = document.getElementById("fullscreenOverlay");
  if (overlay) overlay.style.display = "flex";

  console.warn("⏸ Interview paused (fullscreen violation)");
}



document.addEventListener("fullscreenchange", () => {
  if (interviewCompleted) return;

  if (!document.fullscreenElement) {
    fullscreenExitCount++;

    if (fullscreenExitCount >= MAX_FULLSCREEN_EXIT) {
      alert("❌ Interview terminated (fullscreen violation).");
      finishInterview(true);
      return;
    }

    pauseInterviewForFullscreen();
  }
});



/* ================= TAB SWITCH DETECTION ================= */
document.addEventListener("visibilitychange", () => {
  if (interviewCompleted || interviewPausedForFullscreen) return;

  if (document.hidden) {
    tabSwitchCount++;
    hardStopTTS("tab-switch");
    interviewPaused = true;
    clearInterval(timerInterval);
    alert(
      `⚠️ Tab switching detected.\nWarning ${tabSwitchCount}/${MAX_TAB_SWITCH}`
    );

    if (tabSwitchCount >= MAX_TAB_SWITCH) {
      alert("❌ Interview terminated (tab switching).");
      finishInterview(true);
    }
  }
});


/* ================= TIMER ================= */
const QUESTION_TIME = 60;
let timerInterval;
let timeLeft = QUESTION_TIME;

function startTimer() {
  clearInterval(timerInterval);
  timeLeft = QUESTION_TIME;
  timerEl.innerText = `⏱ ${timeLeft}s`;

  timerInterval = setInterval(() => {
    if (interviewCompleted || interviewPaused) {
      clearInterval(timerInterval);
      return;
    }


    timeLeft--;
    timerEl.innerText = `⏱ ${timeLeft}s`;

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

/* ================= TTS ================= */
function speak(text, onDone) {
  if (interviewPaused || interviewCompleted) return;  // 🔒 BLOCK

  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.95;
  u.pitch = 1;
  u.volume = 1;

  u.onend = () => {
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

const recognition = new SpeechRecognition();
recognition.lang = "en-US";
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

/* ================= CAMERA (MANDATORY) ================= */
async function initCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user" },
      audio: false
    });

    videoEl.srcObject = stream;

    setInterval(() => {
      if (!videoEl.srcObject || videoEl.readyState !== 4) {
        cameraFailureCount++;

        if (cameraFailureCount >= MAX_CAMERA_FAIL) {
          alert("❌ Camera disconnected. Interview terminated.");
          finishInterview(true);
        }
      } else {
        cameraFailureCount = 0;
      }
    }, 3000);

  } catch (e) {
    alert("❌ Camera access is mandatory.");
    finishInterview(true);
  }
}

/* ================= FETCH QUESTION ================= */
async function fetchQuestion(answer = null) {
  if (interviewCompleted || interviewPaused) return;

  try {
    setState("thinking");

    const res = await fetch(`${API_BASE}/ai-interview/next`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_id: candidateId, answer })
    });

    const data = await res.json();

    if (data.completed) {
      interviewCompleted = true;
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

    submitBtn.disabled = false;
    submitBtn.innerText = "Submit";
    showQuestion(data.question, true);

  } catch (e) {
    submitBtn.disabled = false;
    submitBtn.innerText = "Submit";
    alert("Interview error. Refresh if needed.");
  }
}

/* ================= DISPLAY QUESTION ================= */
function showQuestion(q, isFirst = false) {
  if (interviewCompleted) return;

  questionEl.innerText = q;
  answerBox.value = "";
  submitBtn.disabled = false;
  submitBtn.innerText = "Submit";

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

  submitBtn.disabled = true;
  submitBtn.innerText = "Submitting…";
  clearInterval(timerInterval);
  speechSynthesis.cancel();

  fetchQuestion(answer);
}

/* ================= FINISH ================= */
function finishInterview(force = false) {
  if (interviewCompleted) return;

  interviewCompleted = true;


  try {
    mlCamera?.stop();
  } catch {}

  setState("completed");
  clearInterval(timerInterval);
  speechSynthesis.cancel();

  const video = document.getElementById("camera");
  if (video && video.srcObject) {
    video.srcObject.getTracks().forEach(track => track.stop());
    video.srcObject = null;
  }

  questionEl.innerHTML = force
    ? "❌ Interview Terminated"
    : "🎉 Interview Completed";

  answerBox.style.display = "none";
  micBtn.style.display = "none";
  submitBtn.style.display = "none";
  timerEl.innerText = "";

  if (!force) {
    speak("Thank you. Your interview is complete.");
  }
}



/* ================= ML ANTI-CHEAT (STABLE VERSION) ================= */

const canvas = document.getElementById("overlay");
const ctx = canvas.getContext("2d");

let warnings = 0;
const MAX_WARNINGS = 3;

// frame counters
let noFaceFrames = 0;
let multiFaceFrames = 0;
let lookAwayFrames = 0;

// cooldown timers
let lastWarningTime = 0;
const WARNING_COOLDOWN = 5000; // 5 sec

// thresholds (relaxed + human-safe)
const NO_FACE_THRESHOLD = 10;        // 3 sec
const MULTI_FACE_THRESHOLD = 8;    
const LOOK_AWAY_THRESHOLD = 15;     // 6 sec

function now() {
  return Date.now();
}

function canWarn() {
  return now() - lastWarningTime > WARNING_COOLDOWN;
}

function issueWarning(reason) {
  if (!canWarn()) return;

  warnings++;
  lastWarningTime = now();

  interviewPaused = true;
  interviewPausedForFullscreen = true;

  hardStopTTS("warning");
  clearInterval(timerInterval);

  pauseInterviewForFullscreen();
  const overlay = document.getElementById("fullscreenOverlay");
  if (overlay) overlay.style.display = "flex";

  setTimeout(() => {
    alert(`⚠️ Warning ${warnings}/${MAX_WARNINGS}\n${reason}`);
  }, 0);

  if (warnings >= MAX_WARNINGS) {
    terminateInterview("Interview terminated due to repeated violations.");
  }
}





function terminateInterview(reason) {
  setTimeout(() => {
    alert(`❌ ${reason}`);
    finishInterview(true);
  }, 100);
}


/* ---------- FACE MESH (RELAXED EYE TRACKING) ---------- */
const faceMesh = new FaceMesh({
  locateFile: (file) => 
    `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
});

faceMesh.setOptions({
  maxNumFaces: 2,
  refineLandmarks: true,
  minDetectionConfidence: 0.6,
  minTrackingConfidence: 0.6,
});
// --- Gaze calibration ---
let calibrated = false;
let baseDx = 0;
let baseDy = 0;
let calibrationFrames = 0;
const CALIBRATION_REQUIRED = 30;

// smoothing
let dxHistory = [];
let dyHistory = [];
const SMOOTHING_WINDOW = 10;

faceMesh.onResults((res) => {
  const faces = res.multiFaceLandmarks;

  /* =======================
     NO FACE DETECTION
  ======================= */
  if (!faces || faces.length === 0) {
    noFaceFrames++;
    multiFaceFrames = 0;
    lookAwayFrames = 0;

    if (noFaceFrames === 15) {
      issueWarning("Face not detected");
    }
    return;
  } else {
    noFaceFrames = 0;
  }

  /* =======================
     MULTIPLE FACE DETECTION
  ======================= */
  if (faces.length > 1) {
    multiFaceFrames++;
    lookAwayFrames = 0;

    if (multiFaceFrames === 8) {
      issueWarning("Multiple faces detected");
    }
    return;
  } else {
    multiFaceFrames = 0;
  }

const lm = faces[0];

// stable landmarks
const nose = lm[1];
const leftEye = lm[33];
const rightEye = lm[263];

// eye center
const eyeCenterX = (leftEye.x + rightEye.x) / 2;
const eyeCenterY = (leftEye.y + rightEye.y) / 2;

// raw deltas
const dx = Math.abs(nose.x - eyeCenterX);
const dy = Math.abs(nose.y - eyeCenterY);
if (!calibrated) {
  baseDx += dx;
  baseDy += dy;
  calibrationFrames++;

  if (calibrationFrames >= CALIBRATION_REQUIRED) {
    baseDx /= calibrationFrames;
    baseDy /= calibrationFrames;
    calibrated = true;
    console.log("✅ Gaze calibrated", baseDx, baseDy);
  }
  return;
}

// --- SMOOTHING ---
dxHistory.push(dx);
dyHistory.push(dy);
if (dxHistory.length > SMOOTHING_WINDOW) dxHistory.shift();
if (dyHistory.length > SMOOTHING_WINDOW) dyHistory.shift();

const avgDx = dxHistory.reduce((a, b) => a + b, 0) / dxHistory.length;
const avgDy = dyHistory.reduce((a, b) => a + b, 0) / dyHistory.length;

// --- DELTA FROM USER BASELINE ---
const deltaX = Math.abs(avgDx - baseDx);
const deltaY = Math.abs(avgDy - baseDy);

// relaxed human-safe limits
const MAX_DELTA_X = 0.18;
const MAX_DELTA_Y = 0.20;

// sustained violation only
if (deltaX > MAX_DELTA_X || deltaY > MAX_DELTA_Y) {
  lookAwayFrames++;
} else {
  lookAwayFrames = Math.max(0, lookAwayFrames - 4);
}

if (lookAwayFrames >= 45) {
  issueWarning("Please look at the screen");
}
});  


/* ---------- CAMERA PIPELINE ---------- */
const mlCamera = new Camera(videoEl, {
  onFrame: async () => {
    await faceMesh.send({ image: videoEl });
  },
  width: 640,
  height: 480,
});






document.getElementById("resumeFullscreenBtn").onclick = async () => {
  await document.documentElement.requestFullscreen();

  const overlay = document.getElementById("fullscreenOverlay");
  if (overlay) overlay.style.display = "none";

  interviewPaused = false;                 // ✅ RESUME
  interviewPausedForFullscreen = false;

  console.log("▶️ Interview resumed");

  if (interviewCompleted) return;

  if (!questionEl.innerText || questionEl.innerText.includes("Loading")) {
    if (lastQuestionText) {
      questionEl.innerText = lastQuestionText;
    } else {
      fetchQuestion(); 
      return;
    }
  }

  startTimer();

};



/* ================= START INTERVIEW ================= */
window.addEventListener("DOMContentLoaded", () => {
  const startBtn = document.getElementById("startInterviewBtn");

  if (!startBtn) {
    console.error("❌ Start Interview button not found");
    return;
  }

  console.log("✅ Start Interview button ready");

  startBtn.addEventListener("click", async () => {
    try {
      console.log("🔐 Validating interview token...");
      await validateInterviewToken();

      console.log("🚀 Interview started");
      requestFullscreen();

      interviewStarted = true;
      document.getElementById("startScreen")?.remove();

      await initCamera();

      await new Promise(resolve => {
        if (videoEl.readyState >= 2) return resolve();
        videoEl.onloadeddata = () => resolve();
      });

      console.log("📸 Starting ML pipeline");
      mlCamera.start();

      fetchQuestion();
    } catch (e) {
      console.error(e);
    }
  });
});


