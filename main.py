```python
import json
import os
from datetime import datetime

from utils.ai import call_nvidia
from utils.image import fetch_image
from utils.json_fix import repair_json
from utils.rss import fetch_rss


# ===== 讀取設定 =====

with open(
    "config.json",
    "r",
    encoding="utf-8"
) as f:

    config = json.load(f)


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


# ===== 日期 =====

today_display = datetime.now().strftime(
    "%Y-%m-%d"
)

today_file = datetime.now().strftime(
    "%Y-%m%d"
)


# ===== 建立 news 資料夾 =====

os.makedirs(
    "news",
    exist_ok=True
)


# ===== 今日輸出檔案 =====

output_path = f"news/{today_file}.json"


# ===== 如果今日檔案已存在 =====

if os.path.exists(output_path):

    try:

        with open(
            output_path,
            "r",
            encoding="utf-8"
        ) as f:

            results = json.load(f)

    except:

        results = []

else:

    results = []


# ===== 正確流水號 =====

counter = len(results) + 1


# ===== URL 去重 =====

existing_urls = {
    item["url"]
    for item in results
}


# ===== 抓 RSS =====

articles = fetch_rss()


# ===== 主流程 =====

for art in articles:

    # ===== 已存在則跳過 =====

    if art["link"] in existing_urls:

        print(
            f"Skip Duplicate: {art['link']}"
        )

        continue


    # ===== 達到上限 =====

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


        # ===== 加入結果 =====

        results.append(news_item)


        # ===== 更新已存在網址 =====

        existing_urls.add(
            art["link"]
        )


        # ===== 流水號 +1 =====

        counter += 1


        print(
            f"Generated: {news_item['title']}"
        )


    except Exception as e:

        print(f"AI Error: {e}")


# ===== 儲存每日 JSON =====

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


# ===== 讀取 index =====

if os.path.exists(index_path):

    try:

        with open(
            index_path,
            "r",
            encoding="utf-8"
        ) as f:

            index = json.load(f)

    except:

        index = []

else:

    index = []


# ===== 今日資訊 =====

entry = {

    "file": f"{today_file}.json",

    "date": today_display,

    "count": len(results)
}


# ===== 更新或新增 =====

updated = False

for item in index:

    if item["file"] == entry["file"]:

        item["count"] = len(results)

        updated = True

        break


if not updated:

    index.insert(0, entry)


# ===== 儲存 index.json =====

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
```
