import os
import json
import requests
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURATION ---
# 1. Get the API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. Get Webhooks (Handles single link OR multiple links separated by comma)
WEBHOOKS_RAW = os.environ.get("WEBHOOK_URL")
WEBHOOK_LIST = WEBHOOKS_RAW.split(",") if WEBHOOKS_RAW else []

# 3. The HK Tech List
URLS_TO_SCAN = [
    "https://unwire.hk/",
    "https://unwire.pro/",
    "https://www.koc.com.tw/",
    "https://hk.xfastest.com/",
    "https://www.hkepc.com/",
    "https://www.hk01.com/"
]

def run_news_scout():
    if not WEBHOOK_LIST or not GEMINI_API_KEY:
        print("❌ Error: Secrets not found. Check GitHub Settings.")
        return

    client = genai.Client(api_key=GEMINI_API_KEY)
    daily_summary = []
    print("🕵️ News Scout starting...")

    for url in URLS_TO_SCAN:
        try:
            print(f"Scanning: {url}")
            # timeout=10 prevents it from hanging forever if a site is down
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- LINK EXTRACTION LOGIC ---
            links_data = []
            base_domain = url.rstrip("/") 
            
            for a_tag in soup.find_all('a', href=True):
                headline = a_tag.get_text(strip=True)
                link = a_tag['href']
                
                # Filter short junk text
                if len(headline) > 10:
                    # Fix relative links (e.g. "/news/123" -> "https://site.com/news/123")
                    if link.startswith("/"):
                        link = base_domain + link
                    elif not link.startswith("http"):
                        continue 
                    
                    links_data.append(f"HEADLINE: {headline} | LINK: {link}")

            # Limit to 200 links to prevent crashing the AI
            text_content = "\n".join(list(set(links_data))[:200]) 
            
            # --- DEBUG LOGGING (Saves file for you to check later) ---
            # This creates a text file that GitHub will upload as an artifact
            clean_name = base_domain.replace("https://", "").replace("http://", "").replace("/", "")
            with open(f"debug_{clean_name}.txt", "w", encoding="utf-8") as f:
                f.write(f"Source: {url}\n\n{text_content}")
            # -------------------------------------------------------

            # --- GEMINI PROMPT ---
            prompt = f"""
            I am providing a list of links extracted from a website ({url}).
            Format is: "HEADLINE: [Title] | LINK: [Url]"

            Your Goal: 
            1. Filter this list for NEW articles specifically about 'Gemini' (The Google AI).
            2. Ignore generic AI news unless it explicitly mentions Gemini.
            3. If none found, output exactly: "None".
            
            Output Format:
            * [Headline Text](The URL) - Short 1-sentence summary in Traditional Chinese (繁體中文).

            Input Data:
            {text_content}
            """
            
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt
            )
            
            result = response.text.strip()
            
            # Only add to report if it's not "None"
            if "None" not in result and len(result) > 5:
                daily_summary.append(f"*Source: {url}*\n{result}")

        except Exception as e:
            print(f"⚠️ Error scanning {url}: {e}")

    # --- SENDING TO CHAT ---
    if daily_summary:
        final_message = "*🤖 Daily Gemini News Report (HK Edition)*\n\n" + "\n\n".join(daily_summary)
        
        # Loop through all your chat rooms
        for webhook in WEBHOOK_LIST:
            webhook = webhook.strip() # Clean up spaces
            if webhook:
                try:
                    requests.post(webhook, json={"text": final_message})
                    print(f"✅ Sent to: ...{webhook[-10:]}")
                except Exception as e:
                    print(f"❌ Failed to send to chat: {e}")
    else:
        print("No news found today.")

if __name__ == "__main__":
    run_news_scout()
