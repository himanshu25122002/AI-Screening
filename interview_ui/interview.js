/*************************************************
 * GOD-LEVEL AI INTERVIEW ENGINE – interview.js
 * Browser STT + TTS + Camera + AI States
 * NO BACKEND CHANGES REQUIRED
 *************************************************/

const API_BASE = "https://hiring-backend-zku9.onrender.com"; // same backend
const params = new URLSearchParams(window.location.search);
const candidateId = params.get("candidate_id");

if (!candidateId) {
  alert("Missing candidate_id");
  throw new Error("candidate_id missing");
}

/* ---------------- AI STATE MACHINE ---------------- */
let aiState = "idle";
function setState(state) {
  aiState = state;
  document.body.setAttribute("data-state", state);
  console.log("AI STATE →", state);
}

/* ---------------- DOM ELEMENTS ---------------- */
const questionEl = document.getElementById("question");
const answerBox = document.getElementById("answerBox");
const micBtn = document.getElementById("micBtn");
const submitBtn = document.getElementById("submitBtn");
const timerEl = document.getElementById("timer");

/* ---------------- TIMER ---------------- */
const QUESTION_TIME = 60;
let timerInterval;
let timeLeft = QUESTION_TIME;

function startTimer() {
  clearInterval(timerInterval);
  timeLeft = QUESTION_TIME;
  timerEl.innerText = `⏱ ${timeLeft}s`;

  timerInterval = setInterval(() => {
    timeLeft--;
    timerEl.innerText = `⏱ ${timeLeft}s`;

    if (timeLeft <= 0) {
      clearInterval(timerInterval);
      submitAnswer();
    }
  }, 1000);
}

/* ---------------- TTS (SPEECH OUTPUT) ---------------- */
function speak(text) {
  if (!window.speechSynthesis) return;

  speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 0.95;
  utter.pitch = 1.1;
  utter.onstart = () => setState("asking");
  utter.onend = () => setState("idle");

  speechSynthesis.speak(utter);
}

/* ---------------- STT (SPEECH INPUT) ---------------- */
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

if (!SpeechRecognition) {
  alert("Speech Recognition not supported in this browser.");
}

const recognition = new SpeechRecognition();
recognition.lang = "en-US";
recognition.interimResults = false;

micBtn.onclick = () => {
  answerBox.value = "";
  setState("listening");
  recognition.start();
};

recognition.onresult = (event) => {
  const transcript = event.results[0][0].transcript;
  answerBox.value = transcript;
};

recognition.onend = () => {
  setState("idle");
  answerBox.focus();
};

/* ---------------- FETCH QUESTION ---------------- */
async function fetchQuestion(answer = null) {
  try {
    setState("thinking");

    const res = await fetch(`${API_BASE}/ai-interview/next`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        candidate_id: candidateId,
        answer: answer
      })
    });

    if (!res.ok) throw new Error("Interview API failed");

    const data = await res.json();

    if (data.completed) {
      finishInterview();
      return;
    }

    showQuestion(data.question);
  } catch (err) {
    console.error(err);
    alert("Interview error. Please refresh.");
  }
}

/* ---------------- DISPLAY QUESTION ---------------- */
function showQuestion(question) {
  questionEl.innerText = question;
  answerBox.value = "";

  setState("asking");
  speak(question);
  startTimer();
}

/* ---------------- SUBMIT ANSWER ---------------- */
submitBtn.onclick = submitAnswer;

function submitAnswer() {
  clearInterval(timerInterval);
  const answer = answerBox.value.trim();

  if (!answer) {
    alert("Please answer before submitting.");
    return;
  }

  fetchQuestion(answer);
}

/* ---------------- FINISH ---------------- */
function finishInterview() {
  setState("completed");
  clearInterval(timerInterval);

  questionEl.innerHTML = "🎉 Interview Completed";
  answerBox.style.display = "none";
  micBtn.style.display = "none";
  submitBtn.style.display = "none";
  timerEl.innerText = "";

  speak("Thank you. Your interview is now complete.");
}

/* ---------------- CAMERA ---------------- */
async function initCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    const video = document.getElementById("camera");
    video.srcObject = stream;
  } catch (e) {
    console.warn("Camera access denied");
  }
}

/* ---------------- INIT ---------------- */
window.onload = () => {
  initCamera();
  fetchQuestion(); // first question
};
