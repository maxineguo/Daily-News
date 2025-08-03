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
    url_us = f"https://api.nytimes.com/svc/topstories/v2/us.json?api-key={NYTIMES_API_KEY}"
    url_home = f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={NYTIMES_API_KEY}"
    ny_articles = []
    
    try:
        response_us = requests.get(url_us)
        response_us.raise_for_status()
        data_us = response_us.json()
        
        if 'results' in data_us:
            ny_articles.extend(data_us['results'])
        else:
            print("US news response has no 'results' key.")

        response_home = requests.get(url_home)
        response_home.raise_for_status()
        data_home = response_home.json()

        if 'results' in data_home:
            ny_articles.extend(data_home['results'])
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
    
# Script the audio
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=f"You are going to create a script for a news podcast. It should be about 5-10 minutes long(so pretty lenghty). It should be very interesting for the audience. It should be very engaging and fun to listen to. It should be very informative and educational. It should be very well structured and organized. It should be very well written and polished. It should be very well researched and fact-checked from multiple sources. It should be very well presented and delivered. It should be very well produced and edited. Now I have gathered sources and headlines for you to use to make it current. These are a base for you to know what is going on, but you are responsible for actually writing the script. You can use the sources to get more information and details, but you should not copy and paste them. You should use them as a reference and inspiration. You should also use your own knowledge and creativity to make it unique and original. Here is the first source. It is from GNews API: {gnews_headlines()}. Here is the second source. It is from NewsAPI: {newsapi_headlines()}. Here is the third source. It is from New York Times API: {nytimes_headlines()}. Here is the fourth source. It is from Alpha Vantage API for buisness and trading news(you should focus on this slightly less): {alpha_vantage_headlines()}. Here is the fifth source. It is from Weather API(This is the current weather in my area. Just mention it once and be done): {weather()}. Focus on the first 3 sources. Now you can start writing the script. Remember to make it very interesting, engaging, fun, informative, educational, well structured, organized, well written, polished, well researched, fact-checked, presented, delivered, produced and edited.",
)

script = response.text
print(script)