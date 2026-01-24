import streamlit as st
import requests
import json
import time

BACKEND_URL = st.secrets.get("BACKEND_URL", "")

TOTAL_QUESTIONS = 5
QUESTION_TIME_SECONDS = 60  # ⏱ 1 minute per question


def render(candidate_id: str):
    st.set_page_config(page_title="AI Interview", page_icon="🎙️", layout="centered")
    st.title("🎙️ AI Voice Interview")

    # -----------------------------
    # Session state initialization
    # -----------------------------
    if "q_index" not in st.session_state:
        st.session_state.q_index = 1

    if "question" not in st.session_state:
        r = requests.post(
            f"{BACKEND_URL}/ai-interview/next",
            json={"candidate_id": candidate_id}
        )
        r.raise_for_status()
        st.session_state.question = r.json()["question"]

    if "answer" not in st.session_state:
        st.session_state.answer = ""

    # -----------------------------
    # Stop interview if backend says done
    # -----------------------------
    try:
        status_res = requests.get(f"{BACKEND_URL}/candidates/{candidate_id}")
        status_res.raise_for_status()
        status = status_res.json()["data"]["candidate"]["status"]

        if status in ["recommended", "rejected"]:
            st.success("✅ Interview completed. You may safely close this window.")
            st.stop()
    except Exception:
        pass

    # -----------------------------
    # Progress Indicator
    # -----------------------------
    st.progress(st.session_state.q_index / TOTAL_QUESTIONS)
    st.markdown(
        f"### Question {st.session_state.q_index} of {TOTAL_QUESTIONS}"
    )

    # -----------------------------
    # Question + Voice UI
    # -----------------------------
    safe_question = json.dumps(st.session_state.question)

    st.components.v1.html(
        f"""
        <script>
        let timeLeft = {QUESTION_TIME_SECONDS};
        let timer;

        function speak() {{
            speechSynthesis.cancel();
            speechSynthesis.speak(
                new SpeechSynthesisUtterance({safe_question})
            );
        }}

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const rec = new SpeechRecognition();
        rec.lang = "en-US";

        function startRec() {{
            rec.start();
        }}

        rec.onresult = e => {{
            const text = e.results[0][0].transcript;
            document.getElementById("ans").value = text;
        }};

        function startTimer() {{
            timer = setInterval(() => {{
                timeLeft--;
                document.getElementById("timer").innerText =
                    "⏱ Time left: " + timeLeft + "s";

                if (timeLeft <= 0) {{
                    clearInterval(timer);
                    document.getElementById("autoSubmit").click();
                }}
            }}, 1000);
        }}

        window.onload = startTimer;
        </script>

        <h4>Question</h4>
        <p style="font-size:18px;">{st.session_state.question}</p>

        <button onclick="speak()">🔊 Listen</button>
        <button onclick="startRec()">🎙 Speak</button>

        <p id="timer" style="font-weight:bold; color:#d33;"></p>

        <textarea id="ans" rows="4" cols="70"
            placeholder="Your answer will appear here..."></textarea>

        """,
        height=420,
    )

    # -----------------------------
    # Answer box (Streamlit side)
    # -----------------------------
    st.session_state.answer = st.text_area(
        "Edit answer if needed",
        value=st.session_state.answer,
        key=f"answer_{st.session_state.q_index}"
    )

    # -----------------------------
    # Submit logic (manual + auto)
    # -----------------------------
    submit = st.button("Submit Answer", key="submit")
    auto_submit = st.button("AUTO_SUBMIT", key="autoSubmit")

    if submit or auto_submit:
        # 1️⃣ Send answer for evaluation
        requests.post(
            f"{BACKEND_URL}/ai-interview/evaluate",
            json={
                "candidate_id": candidate_id,
                "answer": st.session_state.answer
            }
        ).raise_for_status()

        # 2️⃣ End interview after N questions
        if st.session_state.q_index >= TOTAL_QUESTIONS:
            st.success("🎉 Interview completed. Thank you!")
            st.stop()

        # 3️⃣ Get next question
        r = requests.post(
            f"{BACKEND_URL}/ai-interview/next",
            json={
                "candidate_id": candidate_id,
                "answer": st.session_state.answer
            }
        )
        r.raise_for_status()

        st.session_state.question = r.json()["question"]
        st.session_state.answer = ""
        st.session_state.q_index += 1

        time.sleep(0.5)
        st.experimental_rerun()
