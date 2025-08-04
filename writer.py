# writer.py
import json
import urllib.request
import google.generativeai as genai
import os
from dotenv import load_dotenv, find_dotenv
import requests
from datetime import datetime

now = datetime.now()

def get_api_key():
    dotenv_path = find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path, override=True)
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file or environment variables.")
    return gemini_api_key

def gnews_headlines():
    gnews_api_key = os.getenv("GNEWS_API_KEY")
    if not gnews_api_key:
        print("WARNING: GNEWS_API_KEY not found.")
        return []
    
    category = "general"
    url = f"https://gnews.io/api/v4/top-headlines?category={category}&lang=en&country=us&max=10&apikey={gnews_api_key}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["articles"]
    except Exception as e:
        print(f"Error fetching GNews headlines: {e}")
        return []

def newsapi_headlines():
    newsapi_api_key = os.getenv("NEWSAPI_API_KEY")
    if not newsapi_api_key:
        print("WARNING: NEWSAPI_API_KEY not found.")
        return []

    newsapi_url = (f'https://newsapi.org/v2/top-headlines?'
                   f'country=us&'
                   f'pageSize=10&'
                   f'apiKey={newsapi_api_key}')
    try:
        response = requests.get(newsapi_url)
        response.raise_for_status()
        news_data = response.json()
        if news_data.get('status') == 'ok':
            return news_data['articles']
        else:
            print(f"NewsAPI error: {news_data.get('message', 'Unknown error')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching NewsAPI articles: {e}")
        return []

def nytimes_headlines():
    nytimes_api_key = os.getenv("NYTIMES_API_KEY")
    if not nytimes_api_key:
        print("WARNING: NYTIMES_API_KEY not found.")
        return []

    url_us = f"https://api.nytimes.com/svc/topstories/v2/us.json?api-key={nytimes_api_key}"
    ny_articles = []
    try:
        response_us = requests.get(url_us)
        response_us.raise_for_status()
        data_us = response_us.json()
        if 'results' in data_us:
            ny_articles.extend(data_us['results'])
        return ny_articles
    except requests.exceptions.HTTPError as err:
        print(f"NYTimes HTTP error: {err}")
        return []
    except Exception as err:
        print(f"NYTimes error: {err}")
        return []

def alpha_vantage_headlines():
    alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not alpha_vantage_api_key:
        print("WARNING: ALPHA_VANTAGE_API_KEY not found.")
        return {}

    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&limit=10&sort=RELEVANCE&apikey={alpha_vantage_api_key}"
    r = requests.get(url)
    return r.json()

def weather():
    weather_api_key = os.getenv("WEATHER_API_KEY")
    weather_position = os.getenv("WEATHER_POSITION")
    if not weather_api_key:
        print("WARNING: WEATHER_API_KEY not found.")
        return {}

    if not weather_position:
        print("WARNING: WEATHER_POSITION not found. Defaulting to San Francisco.")
        weather_position = "37.7749,-122.4194"
    
    api_method = 'forecast'
    days = 1
    base_url = "http://api.weatherapi.com/v1"
    url = f"{base_url}/{api_method}.json?key={weather_api_key}&q={weather_position}&days={days}&aqi=no&alerts=yes"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as err:
        print(f"Weather API error: {err}")
        return {}

def generate_podcast_script():
    try:
        gemini_api_key = get_api_key()
        genai.configure(api_key=gemini_api_key)
        client = genai.GenerativeModel("gemini-2.5-flash")
    except ValueError as e:
        return f"Error: {e}"

    try:
        gnews_data = gnews_headlines()
        newsapi_data = newsapi_headlines()
        nytimes_data = nytimes_headlines()
        alpha_vantage_data = alpha_vantage_headlines()
        weather_data = weather()

        if not any([gnews_data, newsapi_data, nytimes_data]):
             script_prompt = (
                "You are a news podcast host. Unfortunately, we're having technical difficulties "
                "with our news feeds. Please generate a fun, engaging, and informative general interest "
                "segment about a recent scientific discovery or a historical event. The segment should "
                "be a few minutes long and be broken into at least 3 paragraphs to provide a good "
                "listening experience for our audience."
             )
        else:
             script_prompt = script_prompt = f"You are going to create a script for a news podcast. It should be about 7-15 minutes long(so pretty lenghty). It should be very interesting for the audience. It should be very engaging and fun to listen to. It should be very informative and educational. It should be very well structured and organized. It should be very well written and polished. It should be very well researched and fact-checked from multiple sources. It should be very well presented and delivered. It should be very well produced and edited. Now I have gathered sources and headlines for you to use to make it current. These are a base for you to know what is going on, but you are responsible for actually writing the script. You can use the sources to get more information and details, but you should not copy and paste them. You should use them as a reference and inspiration. You should also use your own knowledge and creativity to make it unique and original. Here is the first source. It is from GNews API: {gnews_headlines()}. Here is the second source. It is from NewsAPI: {newsapi_headlines()}. Here is the third source. It is from New York Times API: {nytimes_headlines()}. Here is the fourth source. It is from Alpha Vantage API for buisness and trading news(you should focus on this slightly less): {alpha_vantage_headlines()}. Here is the fifth source. It is from Weather API(This is the current weather in my area. Just mention it once and be done): {weather()}. Focus on the first 3 sources. Now you can start writing the script. Remember to make it very interesting, engaging, fun, informative, educational, well structured, organized, well written, polished, well researched, fact-checked, presented, delivered, produced and edited. Remember, today is {now.strftime("%d-%m-%Y")}(date, month, year) so don't assume stuff based on out-dated data or use old sources. Don't repeat information twice even if you see them multiple times in different sources. Make sure it is VERY interesting and fun to listen to. Try to provide as much information as possible but make it detailed - that means make it long. Also, JUST PROVIDE THE SCRIPT. Do not add any extra text or comments. Don't add spaces for sound effects, etc. Focus on the first three sources. Now, write the script. JUST PROVIDE THE SCRIPT. Do not add any extra text or comments. Don't add spaces for sound effects, etc. Do not add stuff like '(SHORT TRANSITION SOUND)' or anything else that is similar. Also, don't name who is talking(ex: host). Also, if you are going to same 'hostname', make up a name. DO NOT just write hostname. This script is going to be directly read so ensure it is properly formatted. ONLY THE TEXT OF THE SCRIPT!!!!!!"

        response = client.generate_content(script_prompt)
        return response.text
    except Exception as e:
        return f"Error generating script: {str(e)}"