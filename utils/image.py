import requests
from bs4 import BeautifulSoup


def fetch_image(url):
    try:
        # 更完整的瀏覽器模擬 headers，避免 403
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # ── 策略1：og:image（最常見）──
        og = soup.find("meta", property="og:image")
        if og and og.get("content", "").startswith("http"):
            return og["content"]

        # ── 策略2：twitter:image ──
        twitter = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter and twitter.get("content", "").startswith("http"):
            return twitter["content"]

        # ── 策略3：twitter:image:src（部分網站用這個）──
        twitter_src = soup.find("meta", attrs={"name": "twitter:image:src"})
        if twitter_src and twitter_src.get("content", "").startswith("http"):
            return twitter_src["content"]

        # ── 策略4：link rel="image_src" ──
        link_img = soup.find("link", rel="image_src")
        if link_img and link_img.get("href", "").startswith("http"):
            return link_img["href"]

        # ── 策略5：文章內第一張圖片（面積夠大才用）──
        for img in soup.find_all("img", src=True):
            src = img.get("src", "")
            if not src.startswith("http"):
                continue
            # 過濾掉 logo、icon、廣告小圖（寬高太小的跳過）
            width  = img.get("width", "0")
            height = img.get("height", "0")
            try:
                if int(width) >= 300 or int(height) >= 200:
                    return src
            except ValueError:
                # 沒有寫寬高的圖片，看 class 或 src 有沒有關鍵字
                skip_keywords = ["logo", "icon", "avatar", "badge", "ad", "banner", "pixel", "tracking"]
                if not any(kw in src.lower() for kw in skip_keywords):
                    return src

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (403, 404):
            print(f"Image Error: HTTP {e.response.status_code} for {url}")
        else:
            print(f"Image Error: {e}")
    except Exception as e:
        print(f"Image Error: {e}")

    return ""
