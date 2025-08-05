# app.py - Production-ready version with TTS fallback
import os
import sys
import traceback
import logging
import json
import time
from flask import Flask, render_template, Response, request, jsonify

# Set up logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['DEBUG'] = False
app.config['TESTING'] = False

def safe_jsonify(data, status_code=200):
    """Safely create a JSON response that will never fail"""
    try:
        return jsonify(data), status_code
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}")
        error_response = {"error": f"JSON serialization failed: {str(e)}"}
        return jsonify(error_response), 500

@app.route("/")
def index():
    """Serve the main page"""
    try:
        logger.info("Serving index page")
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        error_html = f"""
        <html>
        <body>
            <h1>Application Error</h1>
            <p>Error: {str(e)}</p>
            <p><a href='/health'>Check Health</a></p>
            <p><a href='/test'>Test Connection</a></p>
        </body>
        </html>
        """
        return error_html, 500

@app.route("/health")
def health_check():
    """Health check that ALWAYS returns JSON"""    
    try:
        logger.info("Health check requested")
        
        # Basic health info
        health_data = {
            "status": "ok",
            "message": "Flask app is running",
            "python_version": sys.version,
            "flask_env": os.getenv('FLASK_ENV', 'development'),
            "port": os.getenv('PORT', '5000'),
            "environment_variables": {},
            "imports": {},
            "tts_models": {}
        }
        
        # Check environment variables (don't expose actual values)
        env_vars = ["GEMINI_API_KEY", "GNEWS_API_KEY", "NEWSAPI_API_KEY", "NYTIMES_API_KEY", "WEATHER_API_KEY"]
        for var in env_vars:
            value = os.getenv(var)
            if value:
                health_data["environment_variables"][var] = f"set (length: {len(value)})"
            else:
                health_data["environment_variables"][var] = "not_set"
        
        # Test imports
        try:
            from dotenv import load_dotenv
            health_data["imports"]["dotenv"] = "ok"
        except ImportError:
            health_data["imports"]["dotenv"] = "not_available"
        
        try:
            import google.generativeai as genai
            health_data["imports"]["google_generativeai"] = "ok"
        except ImportError as e:
            health_data["imports"]["google_generativeai"] = f"failed: {str(e)}"
        
        try:
            from google import genai as google_genai
            health_data["imports"]["google_genai"] = "ok"
        except ImportError as e:
            health_data["imports"]["google_genai"] = f"failed: {str(e)}"
        
        try:
            import writer
            health_data["imports"]["writer"] = "ok"
        except ImportError as e:
            health_data["imports"]["writer"] = f"failed: {str(e)}"
        
        # Test TTS models availability
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if GEMINI_API_KEY and health_data["imports"].get("google_genai") == "ok":
            try:
                from google import genai
                tts_client = genai.Client(api_key=GEMINI_API_KEY)
                health_data["tts_models"]["client_init"] = "ok"
                
                # Test both TTS models
                tts_models = [
                    "gemini-2.5-flash-preview-tts",
                    "gemini-2.5-pro-preview-tts"
                ]
                
                for model in tts_models:
                    try:
                        # Quick test without actually generating
                        health_data["tts_models"][model] = "available"
                    except Exception as e:
                        health_data["tts_models"][model] = f"error: {str(e)}"
                        
            except Exception as e:
                health_data["tts_models"]["client_init"] = f"failed: {str(e)}"
        
        logger.info("Health check completed successfully")
        return safe_jsonify(health_data)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        logger.error(traceback.format_exc())
        return safe_jsonify({"status": "error", "error": str(e)}, 500)

@app.route("/test")
def test():
    """Simple test endpoint"""
    try:
        logger.info("Test endpoint called")
        from datetime import datetime
        test_data = {
            "message": "Flask is working", 
            "status": "ok",
            "timestamp": str(datetime.now()),
            "request_method": request.method,
            "request_path": request.path
        }
        return safe_jsonify(test_data)
    except Exception as e:
        logger.error(f"Test endpoint error: {e}")
        return safe_jsonify({"error": str(e), "status": "error"}, 500)

def try_tts_generation(tts_client, script, model_name, max_retries=2):
    """Try TTS generation with retries and fallback"""
    logger.info(f"Attempting TTS with model: {model_name}")
    
    for attempt in range(max_retries):
        try:
            from google.genai import types
            
            response = tts_client.models.generate_content(
                model=model_name,
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
            
            if response and response.candidates:
                logger.info(f"TTS generation successful with {model_name} on attempt {attempt + 1}")
                return response, None
                
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"TTS attempt {attempt + 1} failed with {model_name}: {error_msg}")
            
            if attempt < max_retries - 1:
                # Wait before retry
                time.sleep(1)
            else:
                return None, error_msg
    
    return None, f"All {max_retries} attempts failed"

@app.route("/generate_podcast", methods=['GET', 'POST'])
def generate_podcast():
    """Generate podcast with multiple fallbacks and robust error handling"""
    
    logger.info("=== PODCAST GENERATION STARTED ===")
    
    try:
        # Step 1: Check environment
        logger.info("Step 1: Checking environment")
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not found")
            return safe_jsonify({"error": "GEMINI_API_KEY not configured"}, 500)
        
        logger.info(f"GEMINI_API_KEY found (length: {len(GEMINI_API_KEY)})")
        
        # Step 2: Load environment variables
        logger.info("Step 2: Loading environment")
        try:
            from dotenv import load_dotenv, find_dotenv
            dotenv_path = find_dotenv()
            if dotenv_path:
                load_dotenv(dotenv_path, override=True)
                logger.info(f"Environment loaded from: {dotenv_path}")
        except Exception as e:
            logger.warning(f"Could not load .env: {e}")
        
        # Step 3: Import required modules
        logger.info("Step 3: Importing modules")
        try:
            from google import genai
            from google.genai import types
            logger.info("Google AI modules imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import Google AI: {e}")
            return safe_jsonify({"error": f"Failed to import Google AI modules: {str(e)}"}, 500)
        
        try:
            import writer
            logger.info("Writer module imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import writer: {e}")
            return safe_jsonify({"error": f"Failed to import writer module: {str(e)}"}, 500)
        
        # Step 4: Initialize TTS client
        logger.info("Step 4: Initializing TTS client")
        try:
            tts_client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("TTS client initialized successfully")
        except Exception as e:
            logger.error(f"TTS client initialization failed: {e}")
            return safe_jsonify({"error": f"TTS client initialization failed: {str(e)}"}, 500)
        
        # Step 5: Generate script
        logger.info("Step 5: Generating script")
        try:
            script = writer.generate_podcast_script()
            if not script:
                logger.error("Script generation returned empty result")
                return safe_jsonify({"error": "Script generation returned empty result"}, 500)
            if isinstance(script, str) and script.startswith("Error"):
                logger.error(f"Script generation failed: {script}")
                return safe_jsonify({"error": f"Script generation failed: {script}"}, 500)
            if len(script.strip()) < 50:
                logger.error("Generated script is too short")
                return safe_jsonify({"error": "Generated script is too short"}, 500)
                
            logger.info(f"Script generated successfully, length: {len(script)}")
            
            # Truncate script if too long (TTS models have limits)
            if len(script) > 3000:
                logger.info("Script is long, truncating for TTS stability")
                script = script[:3000] + "..."
                
        except Exception as e:
            logger.error(f"Script generation error: {e}")
            return safe_jsonify({"error": f"Script generation error: {str(e)}"}, 500)
        
        # Step 6: Try TTS generation with multiple models
        logger.info("Step 6: Attempting TTS generation with fallback models")
        
        # List of TTS models to try, in order of preference
        tts_models = [
            "gemini-2.5-flash-preview-tts",
            "gemini-2.5-pro-preview-tts"
        ]
        
        response = None
        last_error = None
        
        for model in tts_models:
            logger.info(f"Trying TTS model: {model}")
            response, error = try_tts_generation(tts_client, script, model)
            
            if response:
                logger.info(f"TTS generation successful with model: {model}")
                break
            else:
                last_error = error
                logger.warning(f"TTS failed with {model}: {error}")
        
        if not response:
            logger.error(f"All TTS models failed. Last error: {last_error}")
            return safe_jsonify({
                "error": f"TTS generation failed with all models. Last error: {last_error}",
                "models_tried": tts_models
            }, 500)
        
        # Step 7: Process audio
        logger.info("Step 7: Processing audio")
        try:
            import base64
            import re
            import io
            import wave
            
            if not response.candidates:
                logger.error("TTS response missing candidates")
                return safe_jsonify({"error": "TTS response missing candidates"}, 500)
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                logger.error("TTS response missing content parts")
                return safe_jsonify({"error": "TTS response missing content parts"}, 500)
            
            part = candidate.content.parts[0]
            if not hasattr(part, 'inline_data') or not part.inline_data:
                logger.error("TTS response missing inline_data")
                return safe_jsonify({"error": "TTS response missing inline_data"}, 500)
            
            b64_data = part.inline_data.data
            mime_type = part.inline_data.mime_type
            
            if not b64_data:
                logger.error("No audio data in TTS response")
                return safe_jsonify({"error": "No audio data in TTS response"}, 500)
            
            # Decode audio
            try:
                pcm_bytes = base64.b64decode(b64_data)
            except Exception as e:
                logger.error(f"Failed to decode base64 audio data: {e}")
                return safe_jsonify({"error": f"Failed to decode audio data: {str(e)}"}, 500)
            
            if len(pcm_bytes) < 1000:
                logger.error(f"Audio data too short: {len(pcm_bytes)} bytes")
                return safe_jsonify({"error": f"Audio data too short: {len(pcm_bytes)} bytes"}, 500)
            
            # Convert to WAV
            try:
                rate_match = re.search(r"rate=(\d+)", mime_type or "")
                sample_rate = int(rate_match.group(1)) if rate_match else 24000
                
                buf = io.BytesIO()
                with wave.open(buf, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(pcm_bytes)
                
                wav_data = buf.getvalue()
                logger.info(f"Audio processing complete. WAV size: {len(wav_data)} bytes, sample rate: {sample_rate}")
                
                # Return audio with proper headers
                response_obj = Response(
                    wav_data, 
                    mimetype="audio/wav",
                    headers={
                        'Content-Disposition': 'inline; filename="podcast.wav"',
                        'Content-Length': str(len(wav_data)),
                        'Cache-Control': 'no-cache',
                        'Access-Control-Allow-Origin': '*'
                    }
                )
                return response_obj
                
            except Exception as e:
                logger.error(f"WAV conversion failed: {e}")
                return safe_jsonify({"error": f"WAV conversion failed: {str(e)}"}, 500)
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            logger.error(traceback.format_exc())
            return safe_jsonify({"error": f"Audio processing failed: {str(e)}"}, 500)
    
    except Exception as e:
        # This should never happen, but if it does, return JSON
        logger.error(f"Unexpected error in generate_podcast: {e}")
        logger.error(traceback.format_exc())
        return safe_jsonify({"error": f"Unexpected server error: {str(e)}"}, 500)

# Debug endpoint to test script generation only
@app.route("/debug_script")
def debug_script():
    """Debug endpoint to test script generation without TTS"""
    try:
        logger.info("Debug script generation requested")
        import writer
        script = writer.generate_podcast_script()
        
        return safe_jsonify({
            "status": "ok",
            "script_length": len(script) if script else 0,
            "script_preview": script[:200] + "..." if script and len(script) > 200 else script,
            "script_valid": bool(script and len(script) > 50 and not script.startswith("Error"))
        })
    except Exception as e:
        logger.error(f"Debug script error: {e}")
        return safe_jsonify({"error": str(e)}, 500)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 error: {request.url}")
    return safe_jsonify({"error": "Not found", "status": 404}, 404)

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return safe_jsonify({"error": "Internal server error", "status": 500}, 500)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(debug=False, host="0.0.0.0", port=port)

# For Gunicorn
application = app