import json
import os
from datetime import datetime

from utils.ai import call_nvidia
from utils.image import fetch_image
from utils.json_fix import repair_json
from utils.rss import fetch_rss

# ===== 讀取設定 =====
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# ===== AI Provider Mapping =====
AI_PROVIDER = {
    1: "nvidia",
    2: "gemini",
    3: "openai",
    4: "deepseek"
}

provider = AI_PROVIDER.get(config["ai_provider"], "nvidia")

# ===== 抓 RSS =====
articles = fetch_rss()

# ===== 日期 =====
today_display = datetime.now().strftime("%Y-%m-%d")
today_file    = datetime.now().strftime("%Y-%m%d")

# ===== 建立 news 資料夾 =====
os.makedirs("news", exist_ok=True)

# ===== 讀取今日已有的新聞（累積模式）=====
output_path = f"news/{today_file}.json"

if os.path.exists(output_path):
    with open(output_path, "r", encoding="utf-8") as f:
        results = json.load(f)
else:
    results = []

# ===== 已有的 URL（去重用）=====
existing_urls = {item["url"] for item in results}

# ===== 流水號從現有數量接續 =====
counter = len(results) + 1

# ===== 主流程 =====
for art in articles:

    if len(results) >= config["max_articles"]:
        break

    # URL 去重
    if art["link"] in existing_urls:
        continue

    try:
        raw_text = f"""
標題：
{art['title']}

摘要：
{art['summary']}
"""

        if provider == "nvidia":
            ai_result = call_nvidia(raw_text, config["model"])
        else:
            continue

        data = repair_json(ai_result)

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

        print(f"Generated: {news_item['title']}")

    except Exception as e:
        print(f"AI Error: {e}")

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

# 避免重複，若已存在則更新 count
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
