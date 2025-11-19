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
    "https://www.koc.com.tw/",
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
            
            # --- NEW LOGIC START ---
            links_data = []
            base_domain = url.rstrip("/") # Helps fix relative links like "/news/article"
            
            # Find all links on the page
            for a_tag in soup.find_all('a', href=True):
                headline = a_tag.get_text(strip=True)
                link = a_tag['href']
                
                # Filter out short/empty headlines to save space
                if len(headline) > 10:
                    # Fix relative links (e.g. convert "/news/123" to "https://unwire.hk/news/123")
                    if link.startswith("/"):
                        link = base_domain + link
                    elif not link.startswith("http"):
                        continue # Skip javascript: or mailto: links
                    
                    links_data.append(f"HEADLINE: {headline} | LINK: {link}")

            # Combine into a big text block, limited to first 200 links to prevent errors
            text_content = "\n".join(list(set(links_data))[:200]) 
            # --- NEW LOGIC END ---

            prompt = f"""
            I am providing a list of links extracted from a website ({url}).
            Format is: "HEADLINE: [Title] | LINK: [Url]"

            Your Goal: 
            1. Filter this list for NEW articles specifically about 'Google Gemini'.
            2. If none found, output exactly: "None".
            3. If found, output a bullet point list.
            4. IMPORTANT: You MUST use the exact URL provided in the "LINK:" field.
            
            Format the output like this:
            * [Headline Text](The URL) - Short 1-sentence summary.

            Input Data:
            {text_content}
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
