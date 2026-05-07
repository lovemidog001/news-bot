import requests
from bs4 import BeautifulSoup


def fetch_image(url):

    try:

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # og:image
        og = soup.find(
            "meta",
            property="og:image"
        )

        if og:
            return og.get("content", "")

        # twitter:image
        twitter = soup.find(
            "meta",
            attrs={"name": "twitter:image"}
        )

        if twitter:
            return twitter.get("content", "")

    except Exception as e:
        print(f"Image Error: {e}")

    return ""
