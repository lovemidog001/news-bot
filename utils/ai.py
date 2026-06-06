import os
import re
import json
import time
import requests

def build_prompt(text):
    return f"""
你是一位充滿活力、說話接地氣的專業新聞編輯兼專欄作家，擅長從技術文章中挖掘最核心的價值。
現在要請你將一則英文新聞，轉譯並重編成台灣讀者會大感興趣、兼具深度與趣味的繁體中文報導。

請根據以下內容生成 JSON 格式。

撰寫規則:

1. score（品質評分）
- 請根據「選題、內容、深度、實用、創新、表達」六個維度進行綜合評分。
- 分數範圍為 0~100。
- 只有當內容具備獨特洞察力或極高實用性時，才給予 90 分以上。

2. takeaways（核心觀點）
- 必須是繁體中文。
- 陣列格式，包含 3 個最重要的核心重點。
- 每個重點 20~40 字，要精簡有力，讓讀者能快速掌握價值。

3. punchline（金句）
- 文章中最精闢、最幽默或最具啟發性的一句話。
- 必須是繁體中文。
- 20 字以內，要讓人想轉發分享。

4. title（標題）
- 必須是繁體中文（台灣習慣用語）。
- 15~30字，吸睛、帶有懸念或痛點。
- 嚴禁直接翻譯英文標題，避免農場感。

5. summary（新聞簡介）
- 必須是繁體中文，50~80字。
- 一針見血指出新聞核心與影響。

6. content（新聞內容摘錄 + 幽默生活解析）
- 必須是繁體中文，使用 HTML 格式（包含 <p>、<h2>、<ul>、<li>、<strong> 標籤）。
- 總字數必須在 400 字以上。
- 內文必須包含 2 個 <h2> 結構。
- 結尾統一為：<h2>編輯悄悄話</h2>，用最接地氣、幽默的口吻總結（至少 60 字）。

重要規定:
- 嚴禁出現英文段落，專有名詞除外。
- 內文資訊必須確實根據原文，不可憑空捏造。
- 輸出格式必須是純 JSON，不可包含額外文字。

輸出格式範例:
{{
  "score": 92,
  "takeaways": ["觀點1", "觀點2", "觀點3"],
  "punchline": "這是文章中最好的一句話",
  "title": "吸睛標題",
  "summary": "新聞摘要",
  "content": "<p>內文...</p>"
}}

新聞內容：
{text}
"""

# ── NVIDIA ──
def call_nvidia(text, model="meta/llama-3.1-70b-instruct"):

    api_key = os.getenv("NVIDIA_API_KEY")

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
        "max_tokens": 2000
    }

    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


# ── Gemini ──
def call_gemini(text, model="gemini-1.5-flash"):

    api_key = os.getenv("GEMINI_API_KEY")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": build_prompt(text)
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 2000
        }
    }

    response = requests.post(
        url,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


# ── DeepSeek ──
def call_deepseek(text, model="deepseek-chat"):

    api_key = os.getenv("DEEPSEEK_API_KEY")

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
        "max_tokens": 2000
    }

    response = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


# ── Groq ──
def call_groq(text, model="llama-3.3-70b-versatile"):

    api_key = os.getenv("GROQ_API_KEY")

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
        "max_tokens": 2000
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


# ── Provider 對應表 ──
PROVIDER_MAP = {
    "deepseek": call_deepseek,
    "gemini": call_gemini,
    "groq": call_groq,
    "nvidia": call_nvidia,
}


# ── JSON 安全解析 ──
def safe_json_parse(output: str):

    cleaned = re.sub(r'[\x00-\x1F\x7F]', '', output)

    try:
        return json.loads(cleaned)

    except Exception:

        match = re.search(r'\{.*\}', cleaned, re.DOTALL)

        if match:

            try:
                return json.loads(match.group())

            except Exception:
                return None

    return None


# ── Fallback ──
def call_ai_with_fallback(
    text,
    fallback_chain=["deepseek", "gemini", "groq", "nvidia"]
):

    last_error = None

    for provider in fallback_chain:

        fn = PROVIDER_MAP.get(provider)

        if not fn:
            continue

        try:

            print(f"[Fallback] 嘗試 {provider}...")

            result = fn(text)

            parsed = safe_json_parse(result)

            if not parsed:
                print(f"[Fallback] {provider} JSON 解析失敗")
                continue

            print(f"[Fallback] {provider} 成功")

            return parsed, provider

        except Exception as e:

            print(f"[Fallback] {provider} 失敗：{e}")

            last_error = e

            continue

    raise Exception(f"所有 AI Provider 均失敗：{last_error}")

  
