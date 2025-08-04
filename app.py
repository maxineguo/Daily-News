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

# Load environment variables
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path, override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found. TTS will fail.")
tts_client = genai.Client(api_key=GEMINI_API_KEY)


def wave_bytes(pcm_bytes: bytes, rate: int, channels: int = 1, sample_width: int = 2) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate_podcast", methods=["GET"])
def generate_podcast():
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY not configured."}), 500

    script = generate_podcast_script()
    if script.startswith("Error"):
        return jsonify({"error": script}), 500
    
    if len(script.strip()) < 50:
        return jsonify({"error": "Script too short to generate audio."}), 500

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

        part = response.candidates[0].content.parts[0].inline_data
        base64_data = part.data
        mime_type = part.mime_type

        raw_pcm = base64.b64decode(base64_data)

        if not raw_pcm or len(raw_pcm) < 2000:
            return jsonify({"error": "Audio generation returned empty or too-short data."}), 500

        # 4) Parse sample rate from mime_type
        m = re.search(r"rate=(\d+)", mime_type or "")
        rate = int(m.group(1)) if m else 24000

        # 5) Convert PCM to WAV bytes
        wav_data = wave_bytes(raw_pcm, rate)

        # 6) Stream the WAV back to the browser
        return Response(wav_data, mimetype="audio/wav")

    except Exception as e:
        app.logger.error("TTS error", exc_info=True)
        return jsonify({"error": f"TTS generation failed: {e}"}), 500


if __name__ == "__main__":
    app.run(debug=True)