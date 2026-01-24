import streamlit as st
import requests
import json
import time

BACKEND_URL = st.secrets.get("BACKEND_URL")

QUESTION_TIME_SECONDS = 60  # ⏱ 1 minute per question


def render(candidate_id: str):
    st.set_page_config(
        page_title="AI Interview",
        page_icon="🎙️",
        layout="centered"
    )

    st.title("🎙️ AI Voice Interview")

    # -----------------------------
    # Session state initialization
    # -----------------------------
    if "question" not in st.session_state:
        r = requests.post(
            f"{BACKEND_URL}/ai-interview/next",
            json={"candidate_id": candidate_id}
        )
        r.raise_for_status()

        data = r.json()
        if data.get("completed"):
            st.success("✅ Interview already completed.")
            st.stop()

        st.session_state.question = data["question"]
        st.session_state.current = data["current"]
        st.session_state.total = data["total"]

    if "answer" not in st.session_state:
        st.session_state.answer = ""

    # -----------------------------
    # Progress Indicator
    # -----------------------------
    st.progress(st.session_state.current / st.session_state.total)
    st.caption(
        f"Question {st.session_state.current} of {st.session_state.total}"
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

        const SpeechRecognition =
            window.SpeechRecognition || window.webkitSpeechRecognition;
        const rec = new SpeechRecognition();
        rec.lang = "en-US";

        function startRec() {{
            rec.start();
        }}

        rec.onresult = e => {{
            document.getElementById("ans").value =
                e.results[0][0].transcript;
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
        height=420
    )

    # -----------------------------
    # Answer input (Streamlit side)
    # -----------------------------
    st.session_state.answer = st.text_area(
        "Edit answer if needed",
        value=st.session_state.answer
    )

    # -----------------------------
    # Submit logic (manual + auto)
    # -----------------------------
    submit = st.button("Submit Answer")
    auto_submit = st.button("AUTO_SUBMIT", key="autoSubmit")

    if submit or auto_submit:
        if not st.session_state.answer.strip():
            st.warning("Please provide an answer.")
            st.stop()

        # 🔥 Send evaluation ONLY ON FINAL QUESTION
        if st.session_state.current == st.session_state.total:
            requests.post(
                f"{BACKEND_URL}/ai-interview/evaluate",
                json={
                    "candidate_id": candidate_id,
                    "answer": st.session_state.answer
                }
            ).raise_for_status()

            st.success("🎉 Interview completed successfully!")
            st.markdown(
                """
                Thank you for completing the interview.  
                Our team will review your responses and contact you soon.
                """
            )
            st.stop()

        # 🔁 Get next question
        r = requests.post(
            f"{BACKEND_URL}/ai-interview/next",
            json={
                "candidate_id": candidate_id,
                "answer": st.session_state.answer
            }
        )
        r.raise_for_status()

        data = r.json()

        if data.get("completed"):
            st.success("🎉 Interview completed!")
            st.stop()

        st.session_state.question = data["question"]
        st.session_state.current = data["current"]
        st.session_state.total = data["total"]
        st.session_state.answer = ""

        time.sleep(0.3)
        st.experimental_rerun()
