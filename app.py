# app.py
from flask import Flask, render_template, Response, jsonify, request
import io
import wave
import re
import os
import base64
import traceback
import sys
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# Initialize global variables
tts_client = None
GEMINI_API_KEY = None

def initialize_app():
    """Initialize the app with proper error handling"""
    global tts_client, GEMINI_API_KEY
    
    try:
        from dotenv import load_dotenv, find_dotenv
        dotenv_path = find_dotenv()
        if dotenv_path:
            load_dotenv(dotenv_path, override=True)
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY not configured; TTS will fail.")
        return
    
    try:
        from google import genai
        from google.genai import types
        tts_client = genai.Client(api_key=GEMINI_API_KEY)
        print("TTS client initialized successfully")
    except Exception as e:
        print(f"Error initializing TTS client: {e}")
        tts_client = None

# Initialize on startup
initialize_app()

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
    try:
        return render_template("index.html")
    except Exception as e:
        app.logger.error(f"Error rendering index: {e}")
        return f"Error loading page: {str(e)}", 500

@app.route("/generate_podcast", methods=["GET"])
def generate_podcast():
    """Generate podcast with comprehensive error handling"""
    
    def error_json(msg, code=500):
        app.logger.error(f"Podcast generation error: {msg}")
        return jsonify({"error": msg}), code

    try:
        # Check if required modules are available
        if not GEMINI_API_KEY:
            return error_json("GEMINI_API_KEY not configured.", 500)

        if not tts_client:
            return error_json("TTS client not initialized. Check API key and dependencies.", 500)

        # Import here to catch import errors
        try:
            from google.genai import types
            from writer import generate_podcast_script
        except ImportError as e:
            return error_json(f"Failed to import required modules: {str(e)}", 500)

        # 1) Generate the script
        try:
            app.logger.info("Generating podcast script...")
            script = generate_podcast_script()
            app.logger.info(f"Script generated, length: {len(script) if script else 0}")
        except Exception as e:
            return error_json(f"Script generation failed: {str(e)}", 500)
            
        if not script:
            return error_json("Script generation returned empty result.", 500)
            
        if script.startswith("Error"):
            return error_json(script, 500)
            
        if len(script.strip()) < 50:
            return error_json("Script too short to generate audio.", 500)

        # 2) Call Gemini TTS
        try:
            app.logger.info("Calling Gemini TTS...")
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
            app.logger.info("TTS call completed successfully")
        except Exception as e:
            return error_json(f"TTS call failed: {str(e)}", 500)

        # 3) Extract & base64-decode PCM
        try:
            app.logger.info("Processing TTS response...")
            if not response or not response.candidates:
                return error_json("TTS response is empty or invalid", 500)
                
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                return error_json("TTS response missing content parts", 500)
                
            part = candidate.content.parts[0]
            if not hasattr(part, 'inline_data') or not part.inline_data:
                return error_json("TTS response missing inline_data", 500)
                
            b64 = part.inline_data.data
            mime = part.inline_data.mime_type
            
            if not b64:
                return error_json("TTS response missing audio data", 500)
                
        except Exception as e:
            return error_json(f"TTS response processing failed: {str(e)}", 500)

        try:
            app.logger.info("Decoding base64 audio data...")
            pcm_bytes = base64.b64decode(b64)
            app.logger.info(f"Audio data decoded, size: {len(pcm_bytes)} bytes")
        except Exception as e:
            return error_json(f"Base64 decode failed: {str(e)}", 500)

        if len(pcm_bytes) < 2000:
            return error_json("Audio data too short.", 500)

        # 4) Determine sample rate
        m = re.search(r"rate=(\d+)", mime or "")
        rate = int(m.group(1)) if m else 24000
        app.logger.info(f"Using sample rate: {rate}")

        # 5) Wrap PCM in WAV
        try:
            app.logger.info("Converting to WAV format...")
            wav_data = wav_bytes_from_pcm(pcm_bytes, rate)
            app.logger.info(f"WAV conversion completed, size: {len(wav_data)} bytes")
        except Exception as e:
            return error_json(f"WAV conversion failed: {str(e)}", 500)

        # 6) Stream WAV back to the browser
        app.logger.info("Returning audio response")
        return Response(wav_data, mimetype="audio/wav")
        
    except Exception as e:
        # Catch any unexpected errors and return JSON
        error_msg = f"Unexpected error: {str(e)}"
        app.logger.error(error_msg)
        app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 500

@app.route("/health")
def health_check():
    """Health check endpoint"""
    status = {
        "status": "ok",
        "gemini_api_key_configured": bool(GEMINI_API_KEY),
        "tts_client_initialized": bool(tts_client),
    }
    return jsonify(status)

# Global error handlers
@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith('/generate_podcast') or request.path.startswith('/api/'):
        return jsonify({"error": "API endpoint not found"}), 404
    return "Page not found", 404

@app.errorhandler(500)
def handle_500(e):
    app.logger.error(f"500 error: {str(e)}")
    if request.path.startswith('/generate_podcast') or request.path.startswith('/api/'):
        return jsonify({"error": "Internal server error"}), 500
    return "Internal Server Error", 500

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {str(e)}")
    app.logger.error(traceback.format_exc())
    
    # For API endpoints, always return JSON
    if request.path.startswith('/generate_podcast') or request.path.startswith('/api/'):
        if isinstance(e, HTTPException):
            return jsonify({"error": e.description}), e.code
        return jsonify({"error": "Internal server error"}), 500
    
    # For web pages, return HTML error page
    if isinstance(e, HTTPException):
        return e
    return "Internal Server Error", 500

if __name__ == "__main__":
    # Set up logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # In production, DEBUG should be False
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    port = int(os.getenv("PORT", 5001))
    app.run(debug=debug_mode, host="0.0.0.0", port=port)