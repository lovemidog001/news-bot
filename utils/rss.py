import re
import json
import requests
from bs4 import BeautifulSoup
import feedparser


def fetch_aihot(max_items=5):
    """
    抓取 aihot.virxact.com 精選 AI 新聞
    失敗時回傳空列表，不影響主流程
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get("https://aihot.virxact.com/", headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles = []
        seen = set()

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if not href.startswith("http") or "aihot.virxact.com" in href:
                continue
            if href in seen:
                continue
            seen.add(href)

            title = a.get_text(strip=True)
            if len(title) < 10:
                continue

            parent = a.find_parent()
            summary = ""
            if parent:
                summary = parent.get_text(separator=" ", strip=True)[:300]

            articles.append({
                "title":   title,
                "link":    href,
                "summary": summary,
                "source":  "AI HOT 精選"
            })

            if len(articles) >= max_items:
                break

        print(f"[AIHOT] 抓取 {len(articles)} 篇")
        return articles

    except Exception as e:
        print(f"[AIHOT] 抓取失敗: {e}")
        return []


def extract_full_content(url):
    """
    抓取網頁全文內容 (FeedFuse 核心功能模擬)
    嘗試從網頁中提取最有可能是正文的部分
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        
        # 針對特定錯誤安靜處理，讓主流程切換到摘要模式
        if resp.status_code in [403, 401]:
            return ""
            
        resp.raise_for_status()
        
        # 處理編碼問題
        resp.encoding = resp.apparent_encoding
        
        soup = BeautifulSoup(resp.text, "lxml")
        
        # 移除干擾元素
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "ad"]):
            tag.decompose()

        # 1. 嘗試常見的正文標籤
        content_tags = [
            soup.find("article"),
            soup.find("div", class_=re.compile(r"article|content|post|entry|main-body", re.I)),
            soup.find("main")
        ]
        
        best_tag = next((tag for tag in content_tags if tag), None)
        
        if best_tag:
            paragraphs = best_tag.find_all("p")
            if not paragraphs:
                # 如果有標籤但沒 <p>，直接拿文字
                text = best_tag.get_text(separator="\n", strip=True)
            else:
                text = "\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
        else:
            # 2. 如果找不到明確標籤，則抓取所有的 <p>
            paragraphs = soup.find_all("p")
            if not paragraphs:
                text = soup.get_text(separator="\n", strip=True)
            else:
                text = "\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
        
        # 限制長度，避免 token 爆炸，但提供足夠資訊
        return text[:4000]

    except Exception as e:
        print(f"[Scraper] 抓取全文失敗 ({url}): {e}")
        return ""


def fetch_rss():

    with open("rss_sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)

    articles = []

    # ★ 優先加入 aihot 精選
    aihot_articles = fetch_aihot(5)
    articles.extend(aihot_articles)

    for src in sources:
        try:
            feed = feedparser.parse(src["url"])

            for entry in feed.entries[:1]:
                articles.append({
                    "title":   entry.get("title", ""),
                    "link":    entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "source":  src["name"]
                })

            if len(articles) >= 40:
                break

        except Exception as e:
            print(f"RSS Error: {e}")

    return articles
