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
fallback_chain = config.get(
    "fallback_chain",
    ["deepseek", "gemini", "groq"]
)


# ===== 抓 RSS =====
articles = fetch_rss()


# ===== 日期 =====
today_display = datetime.now().strftime("%Y-%m-%d")
today_file = datetime.now().strftime("%Y-%m%d")


# ===== 建立 news 資料夾 =====
os.makedirs("news", exist_ok=True)


# ===== 今日輸出檔 =====
output_path = f"news/{today_file}.json"


# ===== 讀取舊資料 =====
if os.path.exists(output_path):

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            results = json.load(f)

    except Exception:
        results = []

else:
    results = []


# ===== 已有 URL 去重 =====
existing_urls = {
    item.get("url")
    for item in results
    if isinstance(item, dict)
}


# ===== 流水號 =====
counter = len(results) + 1


# ===== 主流程 =====
for art in articles:

    try:

        # ===== 最大數量 =====
        if len(results) >= config.get("max_articles", 20):
            break

        # ===== 去重 =====
        if art["link"] in existing_urls:
            print(f"Skip Duplicate: {art['link']}")
            continue

        # ===== 原始新聞 =====
        raw_text = f"""
標題：
{art['title']}

摘要：
{art['summary']}
"""

        # ===== AI 生成 =====
        data, used_provider = call_ai_with_fallback(
            raw_text,
            fallback_chain
        )

        # ===== 驗證 =====
        if not isinstance(data, dict):
            print("AI 回傳不是 dict")
            continue

        # ===== 組裝 =====
        news_item = {
            "id": str(counter).zfill(3),

            "title": data.get("title", "").strip(),

            "summary": data.get("summary", "").strip(),

            "content": data.get("content", "").strip(),

            "image": fetch_image(art["link"]),

            "source": art.get("source", ""),

            "url": art["link"],

            "date": today_display
        }

        # ===== 必填檢查 =====
        if (
            not news_item["title"]
            or not news_item["summary"]
            or not news_item["content"]
        ):
            print("AI 回傳缺少必要欄位")
            continue

        # ===== 儲存 =====
        results.append(news_item)

        existing_urls.add(art["link"])

        counter += 1

        print(f"Generated [{used_provider}]：{news_item['title']}")

    except Exception as e:

        print(f"All AI Failed：{e}")

        continue


# ===== 輸出每日 JSON =====
with open(output_path, "w", encoding="utf-8") as f:

    json.dump(
        results,
        f,
        ensure_ascii=False,
        indent=2
    )

print(f"Saved: {output_path}")


# ===== 更新 index.json =====
index_path = "news/index.json"


if os.path.exists(index_path):

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)

    except Exception:
        index = []

else:
    index = []


entry = {
    "file": f"{today_file}.json",
    "date": today_display,
    "count": len(results)
}


# ===== 更新 index =====
exists = False

for i, item in enumerate(index):

    if (
        isinstance(item, dict)
        and item.get("file") == entry["file"]
    ):

        index[i] = entry

        exists = True

        break


if not exists:
    index.insert(0, entry)


# ===== 寫入 index =====
with open(index_path, "w", encoding="utf-8") as f:

    json.dump(
        index,
        f,
        ensure_ascii=False,
        indent=2
    )

print(f"Updated: {index_path}")
