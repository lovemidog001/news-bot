import json
import requests
from bs4 import BeautifulSoup
import feedparser


def fetch_aihot(max_items=5):
    """
    抓取 aihot.virxact.com 精選 AI 新聞
    已有中文摘要，直接當作額外來源
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get("https://aihot.virxact.com/", headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles = []

        # 抓取每則新聞區塊
        # aihot 的結構：每則新聞有標題連結和摘要
        items = soup.find_all("a", href=True)
        seen = set()

        for a in items:
            href = a.get("href", "")
            # 過濾外部新聞連結（非站內連結）
            if not href.startswith("http") or "aihot.virxact.com" in href:
                continue
            if href in seen:
                continue
            seen.add(href)

            title = a.get_text(strip=True)
            if len(title) < 10:
                continue

            # 找同層的摘要文字
            parent = a.find_parent()
            summary = ""
            if parent:
                text = parent.get_text(separator=" ", strip=True)
                summary = text[:300]

            articles.append({
                "title":   title,
                "link":    href,
                "summary": summary,
                "source":  "AI HOT 精選"
            })

            if len(articles) >= max_items:
                break

        print(f"[AIHOT] 抓取 {len(articles)} 篇")
        # ★ 加入 aihot 精選（最多 5 篇）
    aihot_articles = fetch_aihot(5)
    articles = aihot_articles + articles

    return articles

    except Exception as e:
        print(f"[AIHOT] 抓取失敗: {e}")
        return []


def fetch_rss():

    with open(
        "rss_sources.json",
        "r",
        encoding="utf-8"
    ) as f:

        sources = json.load(f)

    articles = []

    for src in sources:

        try:

            feed = feedparser.parse(
                src["url"]
            )

            for entry in feed.entries[:1]:

                articles.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "source": src["name"]
                })
            if len(articles) >= 15:
                return articles
                
        except Exception as e:

            print(f"RSS Error: {e}")

    return articles
