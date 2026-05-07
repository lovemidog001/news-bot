import json
import feedparser
import requests
import os
from datetime import datetime
from bs4 import BeautifulSoup

# ===== 讀設定 =====
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# ===== AI: Gemini =====
def call_gemini(text):
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    model = genai.GenerativeModel(config["model"])

    prompt = f"""
你是一個新聞編輯，請依照以下規範輸出 JSON：

- title：20~40字
- summary：20~50字
- content：HTML格式，兩段<p>
- image：留空字串
- source：來源名稱

內容：
{text}

只輸出 JSON，不要多餘文字
"""

    response = model.generate_content(prompt)
    return response.text

# ===== 抓 RSS =====
def fetch_rss():
    with open("rss_sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)

    articles = []

    for src in sources:
        feed = feedparser.parse(src["url"])
        for entry in feed.entries[:3]:
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "source": src["name"],
                "summary": entry.get("summary", "")
            })

    return articles

# ===== 主流程 =====
def main():
    articles = fetch_rss()
    results = []

    for idx, art in enumerate(articles[:config["max_articles"]]):
        try:
            ai_raw = call_gemini(art["title"] + "\n" + art["summary"])

            data = json.loads(ai_raw)

            results.append({
                "id": str(idx+1).zfill(3),
                "title": data["title"],
                "summary": data["summary"],
                "content": data["content"],
                "image": "",
                "source": art["source"],
                "url": art["link"],
                "date": datetime.now().strftime("%Y-%m-%d")
            })

        except Exception as e:
            print("Error:", e)

    filename = datetime.now().strftime("%Y-%m%d") + ".json"

    os.makedirs("news", exist_ok=True)

    with open(f"news/{filename}", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
