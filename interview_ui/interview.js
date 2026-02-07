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
let interviewPausedForFullscreen = false;

const MAX_FULLSCREEN_EXIT = 3;
const MAX_TAB_SWITCH = 3;
const MAX_CAMERA_FAIL = 3;
let interviewStarted = false;

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

function pauseInterviewForFullscreen() {
  if (interviewCompleted) return;

  interviewPausedForFullscreen = true;
  clearInterval(timerInterval);

  document.getElementById("fullscreenOverlay").style.display = "flex";
}


document.addEventListener("fullscreenchange", () => {
  if (!document.fullscreenElement && !interviewCompleted) {
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
  if (interviewCompleted) return;

  if (document.hidden && document.fullscreenElement) {
    tabSwitchCount++;

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
const NO_FACE_THRESHOLD = 90;        // 3 sec
const MULTI_FACE_THRESHOLD = 120;    // 4 sec
const LOOK_AWAY_THRESHOLD = 180;     // 6 sec

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

  setTimeout(() => {
    alert(`⚠️ Warning ${warnings}/${MAX_WARNINGS}\n${reason}`);
  }, 100); // avoid focus-loop

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

/* ---------- FACE DETECTION ---------- */
const faceDetector = new FaceDetection({
  locateFile: (file) =>
    `https://cdn.jsdelivr.net/npm/@mediapipe/face_detection/${file}`,
});

faceDetector.setOptions({
  model: "short",
  minDetectionConfidence: 0.6,
});

faceDetector.onResults((res) => {
  const count = res.detections?.length || 0;

  noFaceFrames = count === 0 ? noFaceFrames + 1 : 0;
  multiFaceFrames = count > 1 ? multiFaceFrames + 1 : 0;

  if (noFaceFrames > NO_FACE_THRESHOLD) {
    issueWarning("Face not visible. Please stay in frame.");
    noFaceFrames = 0;
  }

  if (multiFaceFrames > MULTI_FACE_THRESHOLD) {
    issueWarning("Multiple faces detected.");
    multiFaceFrames = 0;
  }
});

/* ---------- FACE MESH (RELAXED EYE TRACKING) ---------- */
const faceMesh = new FaceMesh({
  locateFile: (file) =>
    `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
});

faceMesh.setOptions({
  maxNumFaces: 1,
  refineLandmarks: true,
  minDetectionConfidence: 0.6,
  minTrackingConfidence: 0.6,
});

faceMesh.onResults((res) => {
  if (!res.multiFaceLandmarks?.length) return;

  const lm = res.multiFaceLandmarks[0];
  const leftEye = lm[33];
  const rightEye = lm[263];
  const nose = lm[1];

  const eyeCenterX = (leftEye.x + rightEye.x) / 2;
  const eyeCenterY = (leftEye.y + rightEye.y) / 2;

  const dx = Math.abs(nose.x - eyeCenterX);
  const dy = Math.abs(nose.y - eyeCenterY);

  // relaxed thresholds
  if (dx > 0.09 || dy > 0.09) {
    lookAwayFrames++;
  } else {
    lookAwayFrames = Math.max(lookAwayFrames - 2, 0); // decay
  }

  if (lookAwayFrames > LOOK_AWAY_THRESHOLD) {
    issueWarning("Please maintain general attention to the screen.");
    lookAwayFrames = 0;
  }
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


document.getElementById("resumeFullscreenBtn").onclick = () => {
  document.documentElement.requestFullscreen();

  document.getElementById("fullscreenOverlay").style.display = "none";

  interviewPausedForFullscreen = false;

  // Resume timer safely
  startTimer();
};

/* ================= START INTERVIEW ================= */
document.getElementById("startInterviewBtn").onclick = async () => {
  requestFullscreen();

  interviewStarted = true;
  document.getElementById("startScreen").remove();

  await initCamera();
  mlCamera.start(); // 🔥 ensure ML starts AFTER camera ready

  fetchQuestion();
};


