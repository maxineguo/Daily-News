# app.py
import os
import sys
import traceback
import logging
from flask import Flask, render_template, Response, jsonify, request

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Global variables for TTS functionality
tts_client = None
GEMINI_API_KEY = None
genai_types = None
initialization_success = False

def initialize_services():
    """Initialize all services needed for the app"""
    global tts_client, GEMINI_API_KEY, genai_types, initialization_success
    
    logger.info("Starting service initialization...")
    
    try:
        # Load environment variables
        try:
            from dotenv import load_dotenv, find_dotenv
            dotenv_path = find_dotenv()
            if dotenv_path:
                load_dotenv(dotenv_path, override=True)
                logger.info("Environment variables loaded from .env file")
        except ImportError:
            logger.info("python-dotenv not available, using system environment variables")
        except Exception as e:
            logger.warning(f"Could not load .env file: {e}")
        
        # Get API key
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not found in environment variables")
            initialization_success = False
            return False
        
        logger.info("GEMINI_API_KEY found")
        
        # Try to import and initialize Google AI services
        try:
            from google import genai
            from google.genai import types as genai_types_module
            genai_types = genai_types_module
            tts_client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("Google AI services initialized successfully")
            initialization_success = True
            return True
        except ImportError as e:
            logger.error(f"Failed to import Google AI modules: {e}")
            initialization_success = False
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Google AI services: {e}")
            initialization_success = False
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {e}")
        logger.error(traceback.format_exc())
        initialization_success = False
        return False

# Initialize services
logger.info("App starting - initializing services...")
initialize_services()
logger.info(f"Service initialization complete. Success: {initialization_success}")

@app.route("/")
def index():
    """Serve the main page"""
    logger.info("Serving index page")
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Application Error</h1>
            <p>Could not load the main page: {str(e)}</p>
            <p><a href="/health">Check system health</a></p>
        </body>
        </html>
        """, 500

@app.route("/health")
def health_check():
    """Health check endpoint - always returns JSON"""
    logger.info("Health check requested")
    
    try:
        # Collect system information
        status_info = {
            "status": "ok" if initialization_success else "error",
            "timestamp": str(pd.Timestamp.now()) if 'pd' in globals() else "unknown",
            "python_version": sys.version,
            "flask_running": True,
            "environment_checks": {
                "gemini_api_key_configured": bool(GEMINI_API_KEY),
                "tts_client_initialized": bool(tts_client),
                "genai_types_available": bool(genai_types),
                "initialization_success": initialization_success
            },
            "routes_registered": [str(rule) for rule in app.url_map.iter_rules()]
        }
        
        # Try to import writer module
        try:
            import writer
            status_info["writer_module"] = "available"
        except ImportError as e:
            status_info["writer_module"] = f"error: {str(e)}"
        
        return jsonify(status_info)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "error": str(e),
            "flask_running": True
        }), 500

@app.route("/generate_podcast", methods=["GET"])
def generate_podcast():
    """Generate podcast endpoint - always returns JSON or audio"""
    logger.info("Podcast generation requested")
    
    def json_error(message, code=500):
        logger.error(f"Podcast generation error: {message}")
        return jsonify({"error": message}), code
    
    try:
        # Check if services are initialized
        if not initialization_success:
            return json_error("Services not properly initialized. Check /health for details.", 503)
        
        if not GEMINI_API_KEY:
            return json_error("GEMINI_API_KEY not configured", 500)
        
        if not tts_client:
            return json_error("TTS client not available", 500)
        
        # Import writer module
        try:
            logger.info("Importing writer module...")
            import writer
            logger.info("Writer module imported successfully")
        except ImportError as e:
            return json_error(f"Cannot import writer module: {str(e)}", 500)
        
        # Generate script
        logger.info("Generating podcast script...")
        try:
            script = writer.generate_podcast_script()
            logger.info(f"Script generated, length: {len(script) if script else 0}")
        except Exception as e:
            return json_error(f"Script generation failed: {str(e)}", 500)
        
        # Validate script
        if not script:
            return json_error("Script generation returned empty result", 500)
        
        if script.startswith("Error"):
            return json_error(f"Script generation error: {script}", 500)
        
        if len(script.strip()) < 50:
            return json_error("Generated script is too short", 500)
        
        # Generate TTS
        logger.info("Generating TTS audio...")
        try:
            response = tts_client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=script,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=genai_types.SpeechConfig(
                        voice_config=genai_types.VoiceConfig(
                            prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                                voice_name="Kore"
                            )
                        )
                    ),
                ),
            )
            logger.info("TTS generation completed")
        except Exception as e:
            return json_error(f"TTS generation failed: {str(e)}", 500)
        
        # Process TTS response
        logger.info("Processing TTS response...")
        try:
            import base64
            import re
            import io
            import wave
            
            # Extract audio data
            if not response or not response.candidates:
                return json_error("TTS response is empty", 500)
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                return json_error("TTS response missing content", 500)
            
            part = candidate.content.parts[0]
            if not hasattr(part, 'inline_data') or not part.inline_data:
                return json_error("TTS response missing audio data", 500)
            
            b64_data = part.inline_data.data
            mime_type = part.inline_data.mime_type
            
            if not b64_data:
                return json_error("No audio data in TTS response", 500)
            
            # Decode and convert audio
            pcm_bytes = base64.b64decode(b64_data)
            
            if len(pcm_bytes) < 1000:
                return json_error("Audio data is too short", 500)
            
            # Get sample rate and convert to WAV
            rate_match = re.search(r"rate=(\d+)", mime_type or "")
            sample_rate = int(rate_match.group(1)) if rate_match else 24000
            
            # Convert PCM to WAV
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm_bytes)
            
            wav_data = buf.getvalue()
            
            logger.info(f"Audio processing complete. WAV size: {len(wav_data)} bytes")
            
            # Return audio response
            return Response(wav_data, mimetype="audio/wav")
        
        except Exception as e:
            return json_error(f"Audio processing failed: {str(e)}", 500)
    
    except Exception as e:
        logger.error(f"Unexpected error in generate_podcast: {str(e)}")
        logger.error(traceback.format_exc())
        return json_error(f"Unexpected server error: {str(e)}", 500)

# Error handlers
@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    logger.error(f"Unhandled exception on {request.path}: {str(e)}")
    logger.error(traceback.format_exc())
    
    # Return JSON for API endpoints
    if request.path in ['/generate_podcast', '/health'] or request.path.startswith('/api'):
        return jsonify({"error": f"Server error: {str(e)}"}), 500
    
    # HTML response for web pages
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Server Error</title></head>
    <body>
        <h1>Server Error</h1>
        <p>An error occurred: {str(e)}</p>
        <p><a href="/">Go back to home</a></p>
        <p><a href="/health">Check system health</a></p>
    </body>
    </html>
    """, 500

@app.errorhandler(404)
def handle_404(e):
    """Handle 404 errors"""
    logger.warning(f"404 error on {request.path}")
    
    if request.path in ['/generate_podcast', '/health'] or request.path.startswith('/api'):
        return jsonify({"error": "Endpoint not found"}), 404
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Page Not Found</title></head>
    <body>
        <h1>Page Not Found</h1>
        <p>The requested page {request.path} was not found.</p>
        <p><a href="/">Go back to home</a></p>
        <p><a href="/health">Check system health</a></p>
    </body>
    </html>
    """, 404

@app.errorhandler(500)
def handle_500(e):
    """Handle 500 errors"""
    logger.error(f"500 error on {request.path}: {str(e)}")
    
    if request.path in ['/generate_podcast', '/health'] or request.path.startswith('/api'):
        return jsonify({"error": "Internal server error"}), 500
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Internal Server Error</title></head>
    <body>
        <h1>Internal Server Error</h1>
        <p>The server encountered an error.</p>
        <p><a href="/">Go back to home</a></p>
        <p><a href="/health">Check system health</a></p>
    </body>
    </html>
    """, 500

# For Gunicorn
if __name__ == "__main__":
    # Development server
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    port = int(os.getenv("PORT", 5000))
    
    logger.info(f"Starting Flask development server on port {port}, debug={debug_mode}")
    logger.info(f"Service initialization status: {initialization_success}")
    
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
else:
    # Production server (Gunicorn)
    logger.info("Flask app loaded by Gunicorn")
    logger.info(f"Service initialization status: {initialization_success}")
    logger.info(f"Registered routes: {[str(rule) for rule in app.url_map.iter_rules()]}")

# Make sure the app is available for Gunicorn
application = app