# writer.py
import json
import urllib.request
import os
import requests
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

def get_api_key():
    """Get Gemini API key with better error handling"""
    try:
        from dotenv import load_dotenv, find_dotenv
        dotenv_path = find_dotenv()
        if dotenv_path:
            load_dotenv(dotenv_path, override=True)
            logger.info(f"Loaded environment from: {dotenv_path}")
    except ImportError:
        logger.warning("python-dotenv not available, using environment variables only")
    except Exception as e:
        logger.warning(f"Error loading .env file: {e}")
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    
    logger.info(f"GEMINI_API_KEY found (length: {len(gemini_api_key)})")
    return gemini_api_key

def gnews_headlines():
    """Fetch GNews headlines with error handling"""
    gnews_api_key = os.getenv("GNEWS_API_KEY")
    if not gnews_api_key:
        logger.warning("GNEWS_API_KEY not found.")
        return []
    
    category = "general"
    url = f"https://gnews.io/api/v4/top-headlines?category={category}&lang=en&country=us&max=10&apikey={gnews_api_key}"
    try:
        logger.info("Fetching GNews headlines...")
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            articles = data.get("articles", [])
            logger.info(f"GNews: Retrieved {len(articles)} articles")
            return articles
    except urllib.error.HTTPError as e:
        logger.error(f"GNews HTTP error {e.code}: {e.reason}")
        return []
    except urllib.error.URLError as e:
        logger.error(f"GNews URL error: {e.reason}")
        return []
    except Exception as e:
        logger.error(f"Error fetching GNews headlines: {e}")
        return []

def newsapi_headlines():
    """Fetch NewsAPI headlines with error handling"""
    newsapi_api_key = os.getenv("NEWSAPI_API_KEY")
    if not newsapi_api_key:
        logger.warning("NEWSAPI_API_KEY not found.")
        return []

    newsapi_url = (f'https://newsapi.org/v2/top-headlines?'
                   f'country=us&'
                   f'pageSize=10&'
                   f'apiKey={newsapi_api_key}')
    try:
        logger.info("Fetching NewsAPI headlines...")
        response = requests.get(newsapi_url, timeout=15)
        response.raise_for_status()
        news_data = response.json()
        if news_data.get('status') == 'ok':
            articles = news_data.get('articles', [])
            logger.info(f"NewsAPI: Retrieved {len(articles)} articles")
            return articles
        else:
            logger.error(f"NewsAPI error: {news_data.get('message', 'Unknown error')}")
            return []
    except requests.exceptions.HTTPError as e:
        logger.error(f"NewsAPI HTTP error {e.response.status_code}: {e.response.reason}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching NewsAPI articles: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected NewsAPI error: {e}")
        return []

def nytimes_headlines():
    """Fetch NYTimes headlines with error handling"""
    nytimes_api_key = os.getenv("NYTIMES_API_KEY")
    if not nytimes_api_key:
        logger.warning("NYTIMES_API_KEY not found.")
        return []

    url_us = f"https://api.nytimes.com/svc/topstories/v2/us.json?api-key={nytimes_api_key}"
    try:
        logger.info("Fetching NYTimes headlines...")
        response_us = requests.get(url_us, timeout=15)
        response_us.raise_for_status()
        data_us = response_us.json()
        articles = data_us.get('results', [])
        logger.info(f"NYTimes: Retrieved {len(articles)} articles")
        return articles
    except requests.exceptions.HTTPError as err:
        logger.error(f"NYTimes HTTP error {err.response.status_code}: {err.response.reason}")
        return []
    except requests.exceptions.RequestException as err:
        logger.error(f"NYTimes request error: {err}")
        return []
    except Exception as err:
        logger.error(f"Unexpected NYTimes error: {err}")
        return []

def alpha_vantage_headlines():
    """Fetch Alpha Vantage headlines with error handling"""
    alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not alpha_vantage_api_key:
        logger.warning("ALPHA_VANTAGE_API_KEY not found.")
        return {}

    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&limit=10&sort=RELEVANCE&apikey={alpha_vantage_api_key}"
    try:
        logger.info("Fetching Alpha Vantage headlines...")
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        logger.info("Alpha Vantage: Data retrieved successfully")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Alpha Vantage request error: {e}")
        return {}
    except Exception as e:
        logger.error(f"Alpha Vantage error: {e}")
        return {}

def weather():
    """Fetch weather data with error handling"""
    weather_api_key = os.getenv("WEATHER_API_KEY")
    weather_position = os.getenv("WEATHER_POSITION")
    
    if not weather_api_key:
        logger.warning("WEATHER_API_KEY not found.")
        return {}

    if not weather_position:
        logger.warning("WEATHER_POSITION not found. Defaulting to San Francisco.")
        weather_position = "37.7749,-122.4194"
    
    api_method = 'forecast'
    days = 1
    base_url = "http://api.weatherapi.com/v1"
    url = f"{base_url}/{api_method}.json?key={weather_api_key}&q={weather_position}&days={days}&aqi=no&alerts=yes"
    
    try:
        logger.info("Fetching weather data...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        logger.info("Weather: Data retrieved successfully")
        return data
    except requests.exceptions.RequestException as err:
        logger.error(f"Weather API request error: {err}")
        return {}
    except Exception as err:
        logger.error(f"Weather API error: {err}")
        return {}

def generate_podcast_script():
    """Generate podcast script with comprehensive error handling"""
    logger.info("Starting podcast script generation...")
    
    try:
        # Import here to catch import errors
        import google.generativeai as genai
        logger.info("google.generativeai imported successfully")
    except ImportError as e:
        error_msg = f"Error: Failed to import google.generativeai: {str(e)}"
        logger.error(error_msg)
        return error_msg
    
    try:
        gemini_api_key = get_api_key()
        genai.configure(api_key=gemini_api_key)
        client = genai.GenerativeModel("gemini-2.5-flash")
        logger.info("Gemini client initialized successfully")
    except ValueError as e:
        error_msg = f"Error: {e}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error initializing Gemini client: {str(e)}"
        logger.error(error_msg)
        return error_msg

    try:
        logger.info("Fetching news data from all sources...")
        gnews_data = gnews_headlines()
        newsapi_data = newsapi_headlines()
        nytimes_data = nytimes_headlines()
        alpha_vantage_data = alpha_vantage_headlines()
        weather_data = weather()
        
        logger.info(f"Data fetched - GNews: {len(gnews_data)}, NewsAPI: {len(newsapi_data)}, NYTimes: {len(nytimes_data)}, Alpha Vantage: {'yes' if alpha_vantage_data else 'no'}, Weather: {'yes' if weather_data else 'no'}")

        now = datetime.now()
        current_date = now.strftime("%B %d, %Y")
        
        if not any([gnews_data, newsapi_data, nytimes_data]):
            logger.warning("No news data available, generating fallback content")
            script_prompt = (
                "You are a professional news podcast host. Unfortunately, we're experiencing technical difficulties "
                "with our news feeds today. Please generate an engaging, informative segment about a significant "
                "recent scientific discovery or important historical event that happened this week in history. "
                "The segment should be conversational, about 5-7 minutes when spoken, and broken into clear "
                "sections for good listening flow. Make it engaging as if you're talking directly to the listener. "
                f"Today is {current_date}. DO NOT mention technical difficulties or missing news feeds in your script."
            )
        else:
            logger.info("Generating script with available news data")
            script_prompt = f"""You are creating a script for a professional news podcast broadcast. The script should be engaging, informative, and about 7-12 minutes when spoken aloud.

IMPORTANT GUIDELINES:
- Write ONLY the script content that will be read aloud
- Do NOT include any stage directions, sound effect notes, or production notes
- Make it conversational and engaging, as if speaking directly to listeners
- Structure with clear transitions between topics
- Focus primarily on the most significant and interesting stories
- Today is {current_date}

NEWS SOURCES AVAILABLE:
1. GNews Headlines: {json.dumps(gnews_data[:5]) if gnews_data else 'No data available'}
2. NewsAPI Headlines: {json.dumps(newsapi_data[:5]) if newsapi_data else 'No data available'}  
3. New York Times: {json.dumps(nytimes_data[:5]) if nytimes_data else 'No data available'}
4. Business/Finance (Alpha Vantage): {json.dumps(alpha_vantage_data) if alpha_vantage_data else 'No data available'}
5. Weather: {json.dumps(weather_data) if weather_data else 'No data available'}

Create an engaging, well-structured news broadcast script. Focus on the most newsworthy stories, provide context and analysis, and maintain a professional yet conversational tone throughout. The script should flow naturally from one topic to the next."""

        logger.info("Sending request to Gemini...")
        response = client.generate_content(
            script_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=4000,
            )
        )
        
        if response and response.text:
            script = response.text.strip()
            logger.info(f"Script generated successfully, length: {len(script)} characters")
            
            # Validate script quality
            if len(script) < 100:
                error_msg = "Generated script is too short"
                logger.error(error_msg)
                return error_msg
            
            # Remove any unwanted formatting
            script = script.replace("**", "").replace("*", "")
            
            return script
        else:
            error_msg = "Error: Empty response from Gemini"
            logger.error(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Error generating script: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Full traceback: ", exc_info=True)
        return error_msg