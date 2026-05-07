import json
import feedparser
import requests
import os
from datetime import datetime

# ===== 讀設定 =====
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# ===== NVIDIA AI =====
def call_nvidia_ai(text):

    api_key = os.getenv("NVIDIA_API_KEY")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
你是一位專業科技新聞編輯。

請根據以下內容，生成符合規範的 JSON。

規則：

1. title：
- 20~40字
- 像科技新聞標題
- 不要誇張農場感

2. summary：
- 20~50字
- 一句話講重點

3. content：
- HTML格式
- 必須：
<p>第一段</p><p>第二段</p>

4. image：
- 留空字串 ""

5. source：
- 留空字串 ""

只輸出 JSON。
不要 markdown。
不要 ```json。
不要解釋。

格式：

{{
  "title": "",
  "summary": "",
  "content": "",
  "image": "",
  "source": ""
}}

內容：
{text}
"""

    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.6,
        "top_p": 0.9,
        "max_tokens": 800
    }

    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    content = result["choices"][0]["message"]["content"]

    # 清理 markdown
    content = content.replace("```json", "").replace("```", "").strip()

    return content

# ===== 抓文章圖片 =====
def fetch_image(url):

    try:

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, timeout=10)

        html = response.text

        # 找 og:image
        marker = 'property="og:image"'

        if marker in html:

            split_html = html.split(marker)

            if len(split_html) > 1:

                part = split_html[1]

                content_split = part.split('content="')

                if len(content_split) > 1:

                    image_url = content_split[1].split('"')[0]

                    return image_url

    except Exception as e:
        print(f"Image Error: {e}")

    return ""
    
# ===== 抓 RSS =====
def fetch_rss():

    with open("rss_sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)

    articles = []

    for src in sources:

        try:
            feed = feedparser.parse(src["url"])

            for entry in feed.entries[:3]:

                articles.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "source": src["name"]
                })

        except Exception as e:
            print(f"RSS Error: {e}")

    return articles

# ===== 主流程 =====
def main():

    articles = fetch_rss()

    results = []

    today_display = datetime.now().strftime("%Y-%m-%d")
    today_file = datetime.now().strftime("%Y-%m%d")

    for idx, art in enumerate(articles[:config["max_articles"]]):

        try:

            raw_text = f"""
標題：
{art['title']}

摘要：
{art['summary']}
"""

            ai_result = call_nvidia_ai(raw_text)

            data = json.loads(ai_result)

            news_item = {
                "id": str(idx + 1).zfill(3),
                "title": data.get("title", ""),
                "summary": data.get("summary", ""),
                "content": data.get("content", ""),
                "image": fetch_image(art["link"]),
                "source": art["source"],
                "url": art["link"],
                "date": today_display
            }

            results.append(news_item)

            print(f"Generated: {news_item['title']}")

        except Exception as e:
            print(f"AI Error: {e}")

    # 建立資料夾
    os.makedirs("news", exist_ok=True)

    # 輸出 JSON
    output_path = f"news/{today_file}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Saved: {output_path}")

# ===== 啟動 =====
if __name__ == "__main__":
    main()
