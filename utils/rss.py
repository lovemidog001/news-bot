"""
rss.py — RSS 抓取 + 原文擷取
改進：抓取文章原文內容，讓 AI 有更豐富的資料生成高品質新聞
"""

import feedparser
import json
import requests
from bs4 import BeautifulSoup


def fetch_article_content(url: str, timeout: int = 8) -> str:
    """
    抓取文章原文，轉成純文字。
    失敗時回傳空字串，不影響主流程。
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # 移除雜訊標籤
        for tag in soup(["script", "style", "nav", "header", "footer",
                          "aside", "advertisement", "iframe", "noscript"]):
            tag.decompose()

        # 優先找文章主體
        article = (
            soup.find("article")
            or soup.find("main")
            or soup.find(class_=lambda c: c and any(
                k in str(c).lower() for k in ["article", "content", "post", "story", "body"]))
            or soup.find("body")
        )

        if not article:
            return ""

        # 取純文字，限制長度避免 token 爆炸
        text = article.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 30]
        content = "\n".join(lines[:60])  # 最多 60 行

        return content[:3000]  # 最多 3000 字元

    except Exception as e:
        print(f"[RSS] 抓取原文失敗 ({url[:50]}...): {e}")
        return ""


def fetch_rss():
    """
    讀取 rss_sources.json，抓取最新文章。
    每個來源取 1 篇，並嘗試抓取原文內容。
    """
    try:
        with open("rss_sources.json", "r", encoding="utf-8") as f:
            sources = json.load(f)
    except Exception as e:
        print(f"[RSS] 無法讀取 rss_sources.json: {e}")
        return []

    articles = []

    for source in sources:
        if len(articles) >= 40:  # 預先多抓一些，去重後再限制
            break

        try:
            feed = feedparser.parse(source["url"])

            for entry in feed.entries[:1]:  # 每來源 1 篇

                title   = entry.get("title", "").strip()
                summary = entry.get("summary", "") or entry.get("description", "")
                link    = entry.get("link", "")

                if not title or not link:
                    continue

                # 清理 summary HTML
                if summary:
                    soup = BeautifulSoup(summary, "html.parser")
                    summary = soup.get_text(separator=" ", strip=True)[:500]

                # ★ 嘗試抓取原文（增強 AI 輸入品質）
                full_content = fetch_article_content(link)

                articles.append({
                    "title":        title,
                    "summary":      summary,
                    "full_content": full_content,  # 新增：原文內容
                    "link":         link,
                    "source":       source.get("name", "")
                })

        except Exception as e:
            print(f"[RSS] 來源失敗 ({source.get('name', '')}): {e}")
            continue

    print(f"[RSS] 共抓取 {len(articles)} 篇文章")
    return articles
