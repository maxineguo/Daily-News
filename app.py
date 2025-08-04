# app.py
from flask import Flask, render_template, Response, jsonify, request
import io
import wave
import re
import os
import base64
from dotenv import load_dotenv, find_dotenv
from werkzeug.exceptions import HTTPException
import traceback

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
    print("WARNING: GEMINI_API_KEY not configured; TTS will fail.")
tts_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


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

    try:
        if not GEMINI_API_KEY:
            return error_json("GEMINI_API_KEY not configured.", 500)

        if not tts_client:
            return error_json("TTS client not initialized.", 500)

        # 1) Generate the script
        try:
            script = generate_podcast_script()
        except Exception as e:
            return error_json(f"Script generation failed: {str(e)}", 500)
            
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
                                voice_name="Kore"
                            )
                        )
                    ),
                ),
            )
        except Exception as e:
            return error_json(f"TTS call failed: {str(e)}", 500)

        # 3) Extract & base64-decode PCM
        try:
            part = response.candidates[0].content.parts[0].inline_data
            b64 = part.data              # base64-encoded string
            mime = part.mime_type        # e.g. "audio/pcm;rate=24000"
        except Exception as e:
            return error_json(f"TTS response missing audio data: {str(e)}", 500)

        try:
            pcm_bytes = base64.b64decode(b64)
        except Exception as e:
            return error_json(f"Base64 decode failed: {str(e)}", 500)

        if len(pcm_bytes) < 2000:
            return error_json("Audio data too short.", 500)

        # 4) Determine sample rate
        m = re.search(r"rate=(\d+)", mime or "")
        rate = int(m.group(1)) if m else 24000

        # 5) Wrap PCM in WAV
        try:
            wav_data = wav_bytes_from_pcm(pcm_bytes, rate)
        except Exception as e:
            return error_json(f"WAV conversion failed: {str(e)}", 500)

        # 6) Stream WAV back to the browser
        return Response(wav_data, mimetype="audio/wav")
        
    except Exception as e:
        # Catch any unexpected errors and return JSON
        return error_json(f"Unexpected error: {str(e)}", 500)


def is_api_request():
    """Check if the request is for an API endpoint"""
    return request.path.startswith('/generate_podcast') or 'application/json' in request.headers.get('Accept', '')


@app.errorhandler(Exception)
def handle_all_errors(e):
    """Return JSON for any unhandled exceptions, but only for API requests."""
    # For API requests, always return JSON
    if is_api_request():
        if isinstance(e, HTTPException):
            code = e.code
            message = e.description
        else:
            code = 500
            message = str(e)
        
        # Log the error for debugging
        app.logger.error(f"Error in {request.path}: {message}")
        app.logger.error(traceback.format_exc())
        
        return jsonify({"error": message}), code
    
    # For regular web requests, let Flask handle normally
    if isinstance(e, HTTPException):
        return e
    
    # For unexpected errors in web requests, return generic error page
    app.logger.error(f"Unexpected error: {str(e)}")
    app.logger.error(traceback.format_exc())
    return "Internal Server Error", 500


@app.errorhandler(404)
def handle_404(e):
    if is_api_request():
        return jsonify({"error": "API endpoint not found"}), 404
    return "Page not found", 404


@app.errorhandler(500)
def handle_500(e):
    if is_api_request():
        return jsonify({"error": "Internal server error"}), 500
    return "Internal Server Error", 500


if __name__ == "__main__":
    # In production, DEBUG should be False
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_mode)