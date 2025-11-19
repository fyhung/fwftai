import os
import json
import requests
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURATION (READING FROM SECRETS) ---
# We use os.environ.get() to read the hidden passwords from GitHub
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

URLS_TO_SCAN = [
    "https://unwire.hk/",
    "https://unwire.pro/",
    "https://hk.xfastest.com/",
    "https://www.hk01.com/"
]

def run_news_scout():
    if not WEBHOOK_URL or not GEMINI_API_KEY:
        print("❌ Error: Secrets not found. Make sure you added them in GitHub Settings.")
        return

    client = genai.Client(api_key=GEMINI_API_KEY)
    daily_summary = []
    print("🕵️ News Scout starting...")

    for url in URLS_TO_SCAN:
        try:
            print(f"Scanning: {url}")
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove junk
            for script in soup(["script", "style"]):
                script.decompose()
            text_content = soup.get_text()[:50000]

            prompt = f"""
            Scan this website text ({url}) for NEW articles about 'Google Gemini' (the AI model).
            If none, say "None".
            If yes, give 2 bullet points with the headline and link.
            Website Text: {text_content}
            """
            
            # Using the Flash model because it's fast and free-tier friendly
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt
            )
            
            result = response.text.strip()
            if "None" not in result:
                daily_summary.append(f"*Source: {url}*\n{result}")

        except Exception as e:
            print(f"⚠️ Error scanning {url}: {e}")

    if daily_summary:
        final_message = "*🤖 Daily Gemini News Report*\n\n" + "\n\n".join(daily_summary)
        requests.post(WEBHOOK_URL, json={"text": final_message})
        print("✅ Report sent to Chat!")
    else:
        print("No news found today.")

if __name__ == "__main__":
    run_news_scout()
