import json
import os
from datetime import datetime

from utils.ai import call_ai_with_fallback
from utils.image import fetch_image
from utils.rss import fetch_rss

# ===== 讀取設定 =====
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# ===== Fallback 順序 =====
fallback_chain = config.get("fallback_chain", ["nvidia", "gemini", "deepseek"])

# ===== 抓 RSS =====
articles = fetch_rss()
print(f"【Debug】從 RSS 成功抓取到 {len(articles)} 篇新聞")

# ===== 日期 =====
today_display = datetime.now().strftime("%Y-%m-%d")
today_file    = datetime.now().strftime("%Y-%m%d")

# ===== 建立 news 資料夾 =====
os.makedirs("news", exist_ok=True)

# ===== 讀取今日已有的新聞 =====
output_path = f"news/{today_file}.json"

if os.path.exists(output_path):
    with open(output_path, "r", encoding="utf-8") as f:
        results = json.load(f)
else:
    results = []

# ===== 已有的 URL =====
existing_urls = {item["url"] for item in results}
counter = len(results) + 1

print(f"【Debug】目前 config 設定的 max_articles 數量為: {config.get('max_articles')}")
print(f"【Debug】目前今日已累積的新聞數量為: {len(results)}")

# ===== 主流程 =====
for art in articles:

    if len(results) >= config["max_articles"]:
        print("【Debug】已達到 max_articles 限制，主流程中斷停止。")
        break

    # URL 去重
    if art["link"] in existing_urls:
        print(f"Skip Duplicate: {art['link']}")
        continue

    print(f"【Debug】正在嘗試將新聞送給 AI：{art['title']}")

    try:
        raw_text = f"""
標題：
{art['title']}

摘要：
{art['summary']}
"""

        # ★ 使用 Fallback 系統
        ai_result, used_provider = call_ai_with_fallback(
            raw_text, fallback_chain, config["model"]
        )

        data = json.loads(ai_result)

        news_item = {
            "id":      str(counter).zfill(3),
            "title":   data.get("title", ""),
            "summary": data.get("summary", ""),
            "content": data.get("content", ""),
            "image":   fetch_image(art["link"]),
            "source":  art["source"],
            "url":     art["link"],
            "date":    today_display
        }

        results.append(news_item)
        existing_urls.add(art["link"])
        counter += 1

        print(f"Generated [{used_provider}]: {news_item['title']}")

    except Exception as e:
        print(f"All AI Failed 錯誤詳情: {e}")

# ===== 輸出每日 JSON =====
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Saved: {output_path}")

# ===== 更新 index.json =====
index_path = "news/index.json"

if os.path.exists(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)
else:
    index = []

entry = {
    "file":  f"{today_file}.json",
    "date":  today_display,
    "count": len(results)
}

exists = False
for i, item in enumerate(index):
    if isinstance(item, dict) and item.get("file") == entry["file"]:
        index[i]["count"] = len(results)
        exists = True
        break

if not exists:
    index.insert(0, entry)

with open(index_path, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f"Updated: {index_path}")
