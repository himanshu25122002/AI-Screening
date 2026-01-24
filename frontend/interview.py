import streamlit as st
import requests

BACKEND_URL = st.secrets.get("BACKEND_URL", "")

def render(candidate_id: str):
    st.title("AI Voice Interview")

    if "question" not in st.session_state:
        r = requests.post(
            f"{BACKEND_URL}/ai-interview/next",
            json={"candidate_id": candidate_id}
        )
        r.raise_for_status()
        st.session_state.question = r.json()["question"]

    st.components.v1.html(f'''
    <script>
    function speak() {{
      speechSynthesis.speak(
        new SpeechSynthesisUtterance("{st.session_state.question}")
      );
    }}

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SpeechRecognition();
    rec.lang = "en-US";

    function startRec() {{
      rec.start();
    }}

    rec.onresult = e => {{
      document.getElementById("ans").value = e.results[0][0].transcript;
    }};
    </script>

    <h3>Question</h3>
    <p>{st.session_state.question}</p>
    <button onclick="speak()">🔊 Listen</button><br><br>
    <textarea id="ans" rows="4" cols="70"></textarea><br>
    <button onclick="startRec()">🎙 Speak Answer</button>
    ''', height=400)

    answer = st.text_area("Edit answer if needed")

    if st.button("Submit Answer"):
        requests.post(
            f"{BACKEND_URL}/ai-interview/evaluate",
            json={"candidate_id": candidate_id, "answer": answer}
        ).raise_for_status()

        r = requests.post(
            f"{BACKEND_URL}/ai-interview/next",
            json={"candidate_id": candidate_id, "answer": answer}
        )
        r.raise_for_status()

        st.session_state.question = r.json()["question"]
        st.experimental_rerun()
