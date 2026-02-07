/*************************************************
 * GOD-LEVEL AI INTERVIEW ENGINE – interview.js
 * FULLSCREEN + CAMERA + TAB LOCK + STT + TTS
 * ZERO BACKEND CHANGES
 *************************************************/

const API_BASE = "https://ai-screening-wbb0.onrender.com";

const params = new URLSearchParams(window.location.search);
const candidateId = params.get("candidate_id");

let interviewCompleted = false;
let fullscreenExitCount = 0;
let tabSwitchCount = 0;
let cameraFailureCount = 0;

const MAX_FULLSCREEN_EXIT = 3;
const MAX_TAB_SWITCH = 3;
const MAX_CAMERA_FAIL = 3;

if (!candidateId) {
  alert("Missing candidate_id");
  throw new Error("candidate_id missing");
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

/* ================= FULLSCREEN ENFORCEMENT ================= */
function requestFullscreen() {
  const el = document.documentElement;
  if (el.requestFullscreen) el.requestFullscreen();
  else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
}

document.addEventListener("fullscreenchange", () => {
  if (!document.fullscreenElement && !interviewCompleted) {
    fullscreenExitCount++;

    alert(
      `⚠️ Fullscreen is mandatory.\nExit ${fullscreenExitCount}/${MAX_FULLSCREEN_EXIT}`
    );

    if (fullscreenExitCount >= MAX_FULLSCREEN_EXIT) {
      alert("❌ Interview terminated (fullscreen violation).");
      finishInterview(true);
      return;
    }
    requestFullscreen();
  }
});

/* ================= TAB SWITCH DETECTION ================= */
window.addEventListener("blur", () => {
  if (interviewCompleted) return;

  tabSwitchCount++;
  alert(
    `⚠️ Tab switching detected.\nWarning ${tabSwitchCount}/${MAX_TAB_SWITCH}`
  );

  if (tabSwitchCount >= MAX_TAB_SWITCH) {
    alert("❌ Interview terminated (tab switching).");
    finishInterview(true);
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
    if (interviewCompleted) {
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
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.95;
  u.pitch = 1;
  u.volume = 1;
  u.onend = () => onDone && onDone();
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
  if (interviewCompleted) return;

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

    showQuestion(data.question);

  } catch (e) {
    alert("Interview error. Refresh if needed.");
  }
}

/* ================= DISPLAY QUESTION ================= */
function showQuestion(q) {
  if (interviewCompleted) return;

  questionEl.innerText = q;
  answerBox.value = "";
  submitBtn.disabled = false;
  submitBtn.innerText = "Submit";

  setState("asking");

  speak(q, () => {
    if (!interviewCompleted) startTimer();
  });
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
  interviewCompleted = true;

  setState("completed");
  clearInterval(timerInterval);
  speechSynthesis.cancel();

  questionEl.innerHTML = force
    ? "❌ Interview Terminated"
    : "🎉 Interview Completed";

  answerBox.style.display = "none";
  micBtn.style.display = "none";
  submitBtn.style.display = "none";
  timerEl.innerText = "";

  speak(
    force
      ? "Interview terminated due to policy violation."
      : "Thank you. Your interview is complete."
  );
}

/* ================= INIT ================= */
window.onload = async () => {
  requestFullscreen();
  await initCamera();
  fetchQuestion();
};

/* ================= ML ANTI-CHEAT ================= */
const canvas = document.getElementById("overlay");
const ctx = canvas.getContext("2d");

let cheatScore = 0;
const CHEAT_LIMIT = 100;

function flagCheat(reason, weight = 10) {
  cheatScore += weight;
  console.warn("🚨 CHEAT:", reason, cheatScore);

  if (cheatScore >= CHEAT_LIMIT) {
    alert("❌ Interview terminated due to suspicious behavior.");
    finishInterview(true);
  }
}

/* ---------- FACE DETECTION (MULTIPLE PEOPLE) ---------- */
const faceDetector = new FaceDetection({
  locateFile: (file) =>
    `https://cdn.jsdelivr.net/npm/@mediapipe/face_detection/${file}`,
});
faceDetector.setOptions({
  model: "short",
  minDetectionConfidence: 0.7,
});

faceDetector.onResults((res) => {
  if (!res.detections || res.detections.length === 0) {
    flagCheat("No face detected", 8);
  } else if (res.detections.length > 1) {
    flagCheat("Multiple faces detected", 25);
  }
});

/* ---------- FACE MESH (EYES + HEAD POSE) ---------- */
const faceMesh = new FaceMesh({
  locateFile: (file) =>
    `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
});

faceMesh.setOptions({
  maxNumFaces: 1,
  refineLandmarks: true,
  minDetectionConfidence: 0.7,
  minTrackingConfidence: 0.7,
});

faceMesh.onResults((res) => {
  if (!res.multiFaceLandmarks || res.multiFaceLandmarks.length === 0) {
    flagCheat("Face lost", 10);
    return;
  }

  const lm = res.multiFaceLandmarks[0];

  const leftEye = lm[33];
  const rightEye = lm[263];
  const nose = lm[1];

  const eyeCenterX = (leftEye.x + rightEye.x) / 2;
  const eyeCenterY = (leftEye.y + rightEye.y) / 2;

  const dx = Math.abs(nose.x - eyeCenterX);
  const dy = Math.abs(nose.y - eyeCenterY);

  if (dx > 0.05) flagCheat("Looking sideways", 4);
  if (dy > 0.05) flagCheat("Looking down/up", 4);

  canvas.width = videoEl.videoWidth;
  canvas.height = videoEl.videoHeight;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
});

/* ---------- CAMERA PIPELINE ---------- */
const mlCamera = new Camera(videoEl, {
  onFrame: async () => {
    await faceDetector.send({ image: videoEl });
    await faceMesh.send({ image: videoEl });
  },
  width: 640,
  height: 480,
});

mlCamera.start();

