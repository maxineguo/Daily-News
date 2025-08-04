# app.py
import os
import sys
import traceback
import logging
import json
from flask import Flask, render_template, Response, request, jsonify

# Set up logging for production
if os.getenv('FLASK_ENV') == 'production':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
else:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)

# Create Flask app with minimal configuration
app = Flask(__name__)

# Production configuration
if os.getenv('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
else:
    app.config['DEBUG'] = True

def safe_jsonify(data, status_code=200):
    """Safely create a JSON response that will never fail"""
    try:
        return jsonify(data), status_code
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}")
        # Return a minimal error response
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
            "imports": {}
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
        
        # Test writer module functions
        try:
            import writer
            # Test if we can call the main function
            if hasattr(writer, 'generate_podcast_script'):
                health_data["writer_module"] = "generate_podcast_script function available"
            else:
                health_data["writer_module"] = "generate_podcast_script function missing"
        except Exception as e:
            health_data["writer_module"] = f"error: {str(e)}"
        
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
        test_data = {
            "message": "Flask is working", 
            "status": "ok",
            "timestamp": str(datetime.now()) if 'datetime' in globals() else "datetime not imported",
            "request_method": request.method,
            "request_path": request.path
        }
        return safe_jsonify(test_data)
    except Exception as e:
        logger.error(f"Test endpoint error: {e}")
        return safe_jsonify({"error": str(e), "status": "error"}, 500)

@app.route("/generate_podcast", methods=['GET', 'POST'])
def generate_podcast():
    """Generate podcast - bulletproof version that ALWAYS returns JSON or audio"""
    
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
            else:
                logger.info("No .env file found, using system environment")
        except ImportError:
            logger.warning("python-dotenv not available, using environment variables only")
        except Exception as e:
            logger.warning(f"Could not load .env: {e}")
        
        # Step 3: Import required modules
        logger.info("Step 3: Importing Google AI modules")
        try:
            from google import genai
            from google.genai import types
            logger.info("Google AI modules imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import Google AI: {e}")
            return safe_jsonify({"error": f"Failed to import Google AI modules: {str(e)}"}, 500)
        
        # Step 4: Import writer module
        logger.info("Step 4: Importing writer module")
        try:
            import writer
            logger.info("Writer module imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import writer: {e}")
            return safe_jsonify({"error": f"Failed to import writer module: {str(e)}"}, 500)
        
        # Step 5: Initialize TTS client
        logger.info("Step 5: Initializing TTS client")
        try:
            tts_client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("TTS client initialized successfully")
        except Exception as e:
            logger.error(f"TTS client initialization failed: {e}")
            logger.error(traceback.format_exc())
            return safe_jsonify({"error": f"TTS client initialization failed: {str(e)}"}, 500)
        
        # Step 6: Generate script
        logger.info("Step 6: Generating script")
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
        except Exception as e:
            logger.error(f"Script generation error: {e}")
            logger.error(traceback.format_exc())
            return safe_jsonify({"error": f"Script generation error: {str(e)}"}, 500)
        
        # Step 7: Generate TTS
        logger.info("Step 7: Generating TTS")
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
            logger.error(traceback.format_exc())
            return safe_jsonify({"error": f"TTS generation failed: {str(e)}"}, 500)
        
        # Step 8: Process audio
        logger.info("Step 8: Processing audio")
        try:
            import base64
            import re
            import io
            import wave
            
            if not response or not response.candidates:
                logger.error("TTS response is empty")
                return safe_jsonify({"error": "TTS response is empty"}, 500)
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                logger.error("TTS response missing content")
                return safe_jsonify({"error": "TTS response missing content"}, 500)
            
            part = candidate.content.parts[0]
            if not hasattr(part, 'inline_data') or not part.inline_data:
                logger.error("TTS response missing audio data")
                return safe_jsonify({"error": "TTS response missing audio data"}, 500)
            
            b64_data = part.inline_data.data
            mime_type = part.inline_data.mime_type
            
            if not b64_data:
                logger.error("No audio data in TTS response")
                return safe_jsonify({"error": "No audio data in TTS response"}, 500)
            
            # Decode audio
            pcm_bytes = base64.b64decode(b64_data)
            
            if len(pcm_bytes) < 1000:
                logger.error("Audio data is too short")
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
            
            # Return audio with proper headers
            response = Response(
                wav_data, 
                mimetype="audio/wav",
                headers={
                    'Content-Disposition': 'inline; filename="podcast.wav"',
                    'Content-Length': str(len(wav_data)),
                    'Cache-Control': 'no-cache'
                }
            )
            return response
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            logger.error(traceback.format_exc())
            return safe_jsonify({"error": f"Audio processing failed: {str(e)}"}, 500)
    
    except Exception as e:
        # This should never happen, but if it does, return JSON
        logger.error(f"Unexpected error in generate_podcast: {e}")
        logger.error(traceback.format_exc())
        return safe_jsonify({"error": f"Unexpected server error: {str(e)}"}, 500)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 error: {request.url}")
    return safe_jsonify({"error": "Not found", "status": 404}, 404)

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return safe_jsonify({"error": "Internal server error", "status": 500}, 500)

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}")
    logger.error(traceback.format_exc())
    return safe_jsonify({"error": f"Unhandled error: {str(e)}", "status": 500}, 500)

# Add datetime import for test endpoint
from datetime import datetime

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    
    logger.info(f"Starting Flask app on port {port}, debug={debug_mode}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Flask environment: {os.getenv('FLASK_ENV', 'development')}")
    
    app.run(debug=debug_mode, host="0.0.0.0", port=port)

# For Gunicorn - this is critical for Render
application = app