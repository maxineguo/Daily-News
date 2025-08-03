# import
import json
import urllib.request
from google import genai
import os
from dotenv import load_dotenv, find_dotenv
import requests

# Load environment variables from .env file
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path, override=True)
else:
    print("DEBUG: .env file not found. Ensure it's in the project root.")

# Initialize API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWSAPI_API_KEY = os.getenv("NEWSAPI_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NYTIMES_API_KEY = os.getenv("NYTIMES_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_POSITION = os.getenv("WEATHER_POSITION")

if GEMINI_API_KEY:
    client = genai.Client()
else:
    print("WARNING: GEMINI_API_KEY not found in .env. Gemini API calls may fail.")

if not NEWSAPI_API_KEY:
    print("WARNING: NEWSAPI_API_KEY not found in .env. Cannot fetch news articles.")

if not GNEWS_API_KEY:
    print("WARNING: GNEWS_API_KEY not found in .env. Cannot fetch news articles.")

if not NYTIMES_API_KEY:
    print("WARNING: NYTIMES_API_KEY not found in .env. Cannot fetch news articles.")

if not ALPHA_VANTAGE_API_KEY:
    print("WARNING: ALPHA_VANTAGE_API_KEY not found in .env. Cannot fetch stock data.")

if not WEATHER_API_KEY:
    print("WARNING: WEATHER_API_KEY not found in .env. Cannot fetch weather data.")

if not WEATHER_POSITION:
    print("WARNING: WEATHER_POSITION not found in .env. Defaulting to San Francisco coordinates.")
    WEATHER_POSITION = "37.7749,-122.4194"

# Functions to fetch news articles
def gnews_headlines():
    category = "general"
    url = f"https://gnews.io/api/v4/top-headlines?category={category}&lang=en&country=us&max=10&apikey={GNEWS_API_KEY}"

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode("utf-8"))
        articles = data["articles"]

    return articles

def newsapi_headlines():
    newsapi_url = (f'https://newsapi.org/v2/top-headlines?'
                   f'country=us&'
                   f'pageSize=10&'
                   f'apiKey={NEWSAPI_API_KEY}')
    try:
        response = requests.get(newsapi_url)
        response.raise_for_status()
        news_data = response.json()

        if news_data['status'] == 'ok':
            return news_data['articles']
        else:
            print(f"NewsAPI error during global fetch: {news_data.get('message', 'Unknown error')}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching articles globally: {e}")
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from NewsAPI during global fetch.")
        print(f"Raw response: {response.text if 'response' in locals() else 'No response object'}")

def nytimes_headlines():
    urlus = f"https://api.nytimes.com/svc/topstories/v2/us.json?api-key={NYTIMES_API_KEY}"
    urlhome = f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={NYTIMES_API_KEY}"
    ny_articles = []
    
    try:
        response_us = requests.get(url_us)
        response_us.raise_for_status()
        data_us = response_us.json()
        
        if 'results' in data_us:
            ny_articles.extend(data_us['results'])
            print(f"Added {len(data_us['results'])} articles from US.")
        else:
            print("US news response has no 'results' key.")

        response_home = requests.get(url_home)
        response_home.raise_for_status()
        data_home = response_home.json()

        if 'results' in data_home:
            ny_articles.extend(data_home['results'])
            print(f"Added {len(data_home['results'])} articles from Home.")
        else:
            print("Home news response has no 'results' key.")
      
        return ny_articles

    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        return None
    except Exception as err:
        print(f"An error occurred: {err}")
        return None
    
def alpha_vantage_headlines():
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&limit=10&sort=RELEVANCE&apikey={ALPHA_VANTAGE_API_KEY}"
    r = requests.get(url)
    data = r.json()

    return data

def weather():
    api_method='forecast'
    days=1
    base_url = "http://api.weatherapi.com/v1"

    url = f"{base_url}/{api_method}.json?key={WEATHER_API_KEY}&q={WEATHER_POSITION}"
    url += f"&days={days}"
    url += "&aqi=no&alerts=yes"
        
    try:
        response = requests.get(url)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
        print(f"Response Content: {response.text}")
        return None
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
        return None
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
        return None
    except requests.exceptions.RequestException as err:
        print(f"An unexpected error occurred: {err}")
        return None
    
