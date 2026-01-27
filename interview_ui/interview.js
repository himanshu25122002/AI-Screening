// ============================
// CONFIG
// ============================
const API_BASE = "https://hiring-backend-zku9.onrender.com"; // SAME backend
const MAX_TIME = 60;

// ============================
// STATE
// ============================
let candidateId = new URLSearchParams(window.location.search).get("candidate_id");
let timeLeft = MAX_TIME;
let timerInterval;
let recognition;

// ============================
// CAMERA
// ============================
navigator.mediaDevices.getUserMedia({ video: true, audio: false })
  .then(stream => {
    document.getElementById("camera").srcObject = stream;
  })
  .catch(() => alert("Camera access denied"));

// ============================
// SPEECH RECOGNITION (STT)
// ============================
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

recognition = new SpeechRecognition();
recognition.lang = "en-US";
recognition.continuous = false;

recognition.onresult = e => {
  document.getElementById("answerBox").value =
    e.results[0][0].transcript;
};

// ============================
// TTS
// ============================
function speak(text) {
  speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 0.95;
  utter.pitch = 1;
  speechSynthesis.speak(utter);
}

// ============================
// TIMER
// ============================
function startTimer() {
  clearInterval(timerInterval);
  timeLeft = MAX_TIME;
  document.getElementById("timer").innerText = `⏱ ${timeLeft}s`;

  timerInterval = setInterval(() => {
    timeLeft--;
    document.getElementById("timer").innerText = `⏱ ${timeLeft}s`;

    if (timeLeft <= 0) {
      clearInterval(timerInterval);
      submitAnswer();
    }
  }, 1000);
}

// ============================
// API CALLS
// ============================
async function fetchQuestion(answer = null) {
  const res = await fetch(`${API_BASE}/ai-interview/next`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      candidate_id: candidateId,
      answer: answer
    })
  });

  const data = await res.json();

  if (data.completed) {
    document.getElementById("questionText").innerText =
      "Interview completed. Thank you!";
    speak("Interview completed. Thank you.");
    return;
  }

  document.getElementById("questionText").innerText = data.question;
  document.getElementById("answerBox").value = "";

  speak(data.question);
  startTimer();
}

function submitAnswer() {
  const ans = document.getElementById("answerBox").value;
  fetchQuestion(ans);
}

// ============================
// EVENTS
// ============================
document.getElementById("listenBtn").onclick = () =>
  speak(document.getElementById("questionText").innerText);

document.getElementById("micBtn").onclick = () => recognition.start();

document.getElementById("submitBtn").onclick = submitAnswer;

// ============================
// START INTERVIEW
// ============================
fetchQuestion();
