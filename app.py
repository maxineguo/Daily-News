# app.py
import os
import sys
import traceback
import logging
import json
from flask import Flask, render_template, Response, request

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app with minimal configuration
app = Flask(__name__)

def safe_jsonify(data, status_code=200):
    """Safely create a JSON response that will never fail"""
    try:
        response = app.response_class(
            response=json.dumps(data),
            status=status_code,
            mimetype='application/json'
        )
        return response
    except Exception as e:
        # If even this fails, return a plain text response
        return app.response_class(
            response=f'{{"error": "JSON serialization failed: {str(e)}"}}',
            status=500,
            mimetype='application/json'
        )

@app.route("/")
def index():
    """Serve the main page"""
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        return f"<html><body><h1>Error</h1><p>{str(e)}</p><p><a href='/health'>Check Health</a></p></body></html>", 500

@app.route("/health")
def health_check():
    """Health check that ALWAYS returns JSON"""    
    try:
        # Basic health info
        health_data = {
            "status": "ok",
            "message": "Flask app is running",
            "python_version": sys.version,
            "environment_variables": {},
            "imports": {}
        }
        
        # Check environment variables
        env_vars = ["GEMINI_API_KEY", "GNEWS_API_KEY", "NEWSAPI_API_KEY", "NYTIMES_API_KEY"]
        for var in env_vars:
            health_data["environment_variables"][var] = "set" if os.getenv(var) else "not_set"
        
        # Test imports
        try:
            from dotenv import load_dotenv
            health_data["imports"]["dotenv"] = "ok"
        except ImportError:
            health_data["imports"]["dotenv"] = "not_available"
        
        try:
            from google import genai
            health_data["imports"]["google_genai"] = "ok"
        except ImportError as e:
            health_data["imports"]["google_genai"] = f"failed: {str(e)}"
        
        try:
            import writer
            health_data["imports"]["writer"] = "ok"
        except ImportError as e:
            health_data["imports"]["writer"] = f"failed: {str(e)}"
        
        return safe_jsonify(health_data)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return safe_jsonify({"status": "error", "error": str(e)}, 500)

@app.route("/generate_podcast")
def generate_podcast():
    """Generate podcast - bulletproof version that ALWAYS returns JSON or audio"""
    
    # This function will NEVER raise an exception and will ALWAYS return a proper response
    try:
        logger.info("=== PODCAST GENERATION STARTED ===")
        
        # Step 1: Check environment
        logger.info("Step 1: Checking environment")
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not found")
            return safe_jsonify({"error": "GEMINI_API_KEY not configured"}, 500)
        
        logger.info("GEMINI_API_KEY found")
        
        # Step 2: Import required modules
        logger.info("Step 2: Importing modules")
        try:
            from dotenv import load_dotenv, find_dotenv
            dotenv_path = find_dotenv()
            if dotenv_path:
                load_dotenv(dotenv_path, override=True)
            logger.info("Environment loaded")
        except Exception as e:
            logger.warning(f"Could not load .env: {e}")
        
        try:
            from google import genai
            from google.genai import types
            logger.info("Google AI modules imported")
        except ImportError as e:
            logger.error(f"Failed to import Google AI: {e}")
            return safe_jsonify({"error": f"Failed to import Google AI modules: {str(e)}"}, 500)
        
        try:
            import writer
            logger.info("Writer module imported")
        except ImportError as e:
            logger.error(f"Failed to import writer: {e}")
            return safe_jsonify({"error": f"Failed to import writer module: {str(e)}"}, 500)
        
        # Step 3: Initialize TTS client
        logger.info("Step 3: Initializing TTS client")
        try:
            tts_client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("TTS client initialized")
        except Exception as e:
            logger.error(f"TTS client initialization failed: {e}")
            return safe_jsonify({"error": f"TTS client initialization failed: {str(e)}"}, 500)
        
        # Step 4: Generate script
        logger.info("Step 4: Generating script")
        try:
            script = writer.generate_podcast_script()
            if not script:
                return safe_jsonify({"error": "Script generation returned empty result"}, 500)
            if script.startswith("Error"):
                return safe_jsonify({"error": f"Script generation failed: {script}"}, 500)
            if len(script.strip()) < 50:
                return safe_jsonify({"error": "Generated script is too short"}, 500)
            logger.info(f"Script generated successfully, length: {len(script)}")
        except Exception as e:
            logger.error(f"Script generation error: {e}")
            return safe_jsonify({"error": f"Script generation error: {str(e)}"}, 500)
        
        # Step 5: Generate TTS
        logger.info("Step 5: Generating TTS")
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
            logger.info("TTS generation completed")
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return safe_jsonify({"error": f"TTS generation failed: {str(e)}"}, 500)
        
        # Step 6: Process audio
        logger.info("Step 6: Processing audio")
        try:
            import base64
            import re
            import io
            import wave
            
            if not response or not response.candidates:
                return safe_jsonify({"error": "TTS response is empty"}, 500)
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                return safe_jsonify({"error": "TTS response missing content"}, 500)
            
            part = candidate.content.parts[0]
            if not hasattr(part, 'inline_data') or not part.inline_data:
                return safe_jsonify({"error": "TTS response missing audio data"}, 500)
            
            b64_data = part.inline_data.data
            mime_type = part.inline_data.mime_type
            
            if not b64_data:
                return safe_jsonify({"error": "No audio data in TTS response"}, 500)
            
            # Decode audio
            pcm_bytes = base64.b64decode(b64_data)
            
            if len(pcm_bytes) < 1000:
                return safe_jsonify({"error": "Audio data is too short"}, 500)
            
            # Convert to WAV
            rate_match = re.search(r"rate=(\d+)", mime_type or "")
            sample_rate = int(rate_match.group(1)) if rate_match else 24000
            
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm_bytes)
            
            wav_data = buf.getvalue()
            logger.info(f"Audio processing complete. WAV size: {len(wav_data)} bytes")
            
            # Return audio
            return Response(wav_data, mimetype="audio/wav")
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return safe_jsonify({"error": f"Audio processing failed: {str(e)}"}, 500)
    
    except Exception as e:
        # This should never happen, but if it does, return JSON
        logger.error(f"Unexpected error in generate_podcast: {e}")
        logger.error(traceback.format_exc())
        return safe_jsonify({"error": f"Unexpected server error: {str(e)}"}, 500)

# Simple route to test if Flask is working
@app.route("/test")
def test():
    """Simple test endpoint"""
    return safe_jsonify({"message": "Flask is working", "status": "ok"})

# No error handlers - we handle everything at the route level

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(debug=False, host="0.0.0.0", port=port)

# For Gunicorn
application = app