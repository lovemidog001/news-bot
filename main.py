import json
import os
from datetime import datetime

from utils.ai import call_nvidia
from utils.image import fetch_image
from utils.json_fix import repair_json
from utils.rss import fetch_rss


# ===== 讀取設定 =====

try:

    with open(
        index_path,
        "r",
        encoding="utf-8"
    ) as f:

        index = json.load(f)

except:

    index = []


# ===== AI Provider Mapping =====

AI_PROVIDER = {
    1: "nvidia",
    2: "gemini",
    3: "openai",
    4: "deepseek"
}


provider = AI_PROVIDER.get(
    config["ai_provider"],
    "nvidia"
)


# ===== 抓 RSS =====

articles = fetch_rss()


# ===== 結果 =====

results = []


# ===== 日期 =====

today_display = datetime.now().strftime(
    "%Y-%m-%d"
)

today_file = datetime.now().strftime(
    "%Y-%m%d"
)


# ===== 正確流水號 =====

counter = 1


# ===== 主流程 =====

for art in articles:

    if len(results) >= config["max_articles"]:
        break

    try:

        raw_text = f"""
標題：
{art['title']}

摘要：
{art['summary']}
"""

        # ===== AI 呼叫 =====

        if provider == "nvidia":

            ai_result = call_nvidia(
                raw_text,
                config["model"]
            )

        else:
            continue


        # ===== 修復 JSON =====

        data = repair_json(ai_result)


        # ===== 組合新聞 =====

        news_item = {

            "id": str(counter).zfill(3),

            "title": data.get(
                "title",
                ""
            ),

            "summary": data.get(
                "summary",
                ""
            ),

            "content": data.get(
                "content",
                ""
            ),

            "image": fetch_image(
                art["link"]
            ),

            "source": art["source"],

            "url": art["link"],

            "date": today_display
        }


        results.append(news_item)

        counter += 1

        print(
            f"Generated: {news_item['title']}"
        )

    except Exception as e:

        print(f"AI Error: {e}")


# ===== 建立 news 資料夾 =====

os.makedirs(
    "news",
    exist_ok=True
)


# ===== 輸出每日 JSON =====

output_path = f"news/{today_file}.json"

with open(
    output_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        results,
        f,
        ensure_ascii=False,
        indent=2
    )


# ===== index.json =====

index_path = "news/index.json"


# 讀取舊 index

if os.path.exists(index_path):

    with open(
        index_path,
        "r",
        encoding="utf-8"
    ) as f:

        index = json.load(f)

else:

    index = []


# 新增今日資訊

entry = {

    "file": f"{today_file}.json",

    "date": today_display,

    "count": len(results)
}


# 避免重複

exists = any(
    item["file"] == entry["file"]
    for item in index
)


if not exists:

    index.insert(0, entry)


# 存回 index.json

with open(
    index_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        index,
        f,
        ensure_ascii=False,
        indent=2
    )


print(f"Saved: {output_path}")
