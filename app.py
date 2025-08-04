# app.py
from flask import Flask, render_template, Response, jsonify
import io
import wave
import re
import os
import base64
from dotenv import load_dotenv, find_dotenv

from google import genai
from google.genai import types

from writer import generate_podcast_script

app = Flask(__name__)

# Load .env
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path, override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not set; TTS will fail.")
tts_client = genai.Client(api_key=GEMINI_API_KEY)


def wav_bytes_from_pcm(pcm: bytes, rate: int, channels: int = 1, sample_width: int = 2) -> bytes:
    """Convert raw PCM bytes into a WAV container (in-memory)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate_podcast", methods=["GET"])
def generate_podcast():
    def error_json(msg, code=500):
        return jsonify({"error": msg}), code

    if not GEMINI_API_KEY:
        return error_json("GEMINI_API_KEY not configured.", 500)

    # 1) Create the script
    script = generate_podcast_script()
    if script.startswith("Error"):
        return error_json(script, 500)
    if len(script.strip()) < 50:
        return error_json("Script too short to generate audio.", 500)

    # 2) Call Gemini TTS
    try:
        response = tts_client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=script,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Fenrir"
                        )
                    )
                ),
            ),
        )
    except Exception as e:
        return error_json(f"TTS call failed: {e}", 500)

    # 3) Extract & base64-decode the PCM
    try:
        part = response.candidates[0].content.parts[0].inline_data
        b64 = part.data              # a base64-encoded str
        mime = part.mime_type        # e.g. "audio/pcm;rate=24000"
    except Exception:
        return error_json("TTS response missing audio data.", 500)

    try:
        pcm_bytes = base64.b64decode(b64)
    except Exception as e:
        return error_json(f"Base64 decode failed: {e}", 500)

    if len(pcm_bytes) < 2000:
        return error_json("Audio data too short.", 500)

    # 4) Parse sample rate
    m = re.search(r"rate=(\d+)", mime or "")
    rate = int(m.group(1)) if m else 24000

    # 5) Wrap PCM in WAV
    wav_data = wav_bytes_from_pcm(pcm_bytes, rate)

    # 6) Stream WAV
    return Response(wav_data, mimetype="audio/wav")

if __name__ == "__main__":
    app.run(debug=True)