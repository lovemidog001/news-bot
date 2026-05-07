import json
import feedparser


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

            for entry in feed.entries[:3]:

                articles.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "source": src["name"]
                })

        except Exception as e:

            print(f"RSS Error: {e}")

    return articles
