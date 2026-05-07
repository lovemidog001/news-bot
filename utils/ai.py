import os
import requests


def build_prompt(text):

    return f"""
你是一位專業科技新聞編輯。

請根據以下內容生成 JSON。

規則：

1. title
- 20~40字
- 科技新聞風格
- 不要農場感

2. summary
- 20~50字
- 一句話重點

3. content
- HTML格式
- 必須：
<p>第一段</p><p>第二段</p>

4. image
- 留空字串

5. source
- 留空字串

只輸出 JSON。
不要 markdown。
不要解釋。

格式：

{{
  "title": "",
  "summary": "",
  "content": "",
  "image": "",
  "source": ""
}}

內容：
{text}
"""


def call_nvidia(text, model):

    api_key = os.getenv(
        "NVIDIA_API_KEY"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": build_prompt(text)
            }
        ],
        "temperature": 0.6,
        "top_p": 0.9,
        "max_tokens": 800
    }

    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    return result["choices"][0]["message"]["content"]
