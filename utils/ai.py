import os
import re
import json
import time
import requests

def build_prompt(text):
    return f"""
你是一位充滿活力、說話接地氣的專業新聞編輯兼專欄作家。現在要請你將一則英文新聞，轉譯並重編成台灣讀者會大感興趣、兼具深度與趣味的繁體中文報導。

請根據以下內容生成 JSON 格式。

撰寫規則:

1. title（標題）
- 必須是繁體中文（台灣習慣用語，例如：品質、螢幕、數據、安全，而非質量、屏幕）。
- 15~30字。
- 必須吸睛、帶有懸念或痛點，並且包含具體元素（技術名稱、公司、產品或事件主體）。
- 嚴禁直接翻譯英文標題，嚴禁套路化（如「別再盲目跟風！」），避免農場感、問句結尾或過度誇大字眼。

2. summary（新聞簡介）
- 必須是繁體中文，50~80字。
- 一針見血指出新聞核心，說明這件事會造成什麼重大改變。
- 必須包含一個動態動詞（顛覆、推進、挑戰、重塑、衝擊）。
- 避免與標題重複用語。

3. content（新聞內容摘錄 + 幽默生活解析）
- 必須是繁體中文，使用 HTML 格式（包含 <p>、<h2>、<ul>、<li>、<strong> 標籤）。
- 總字數必須在 400 字以上。
- 語氣要像資深編輯在跟朋友聊天，生活化、口語化，但分析要到位。
- 不可使用「根據報導」、「據悉」等死板開頭。
- 內文必須嚴格包含2個 <h2> 結構，依新聞類型選擇對應的小標題：

- 小標題必須：
    緊扣新聞核心，讓讀者快速理解段落重點
    風格生活化、口語化，避免官腔或過度學術
    三個小標題之間要有差異，避免重複或過度相似

4. 不分類，結尾統一：
  * <h2>編輯悄悄話</h2>
    <p>生活趣味口語結論！用最接地氣、幽默的口吻，總結這場事件，給讀者一個有趣的反思，至少 60 字。</p>

- 每個段落至少包含一個 <strong> 關鍵句，讓讀者快速抓到重點。
- 禁止使用 emoji 或網路流行語。

重要規定:
- 嚴禁出現英文段落，專有名詞（如 AI, Apple, Google, Costco）除外。
- 內文資訊必須確實根據原文，不可憑空捏造。
- 所有 JSON 欄位必須填滿，不可留空字串。
- 語氣需兼顧新聞編輯的專業中立，避免主觀情緒判斷。

輸出格式:
{{
  "title": "",
  "summary": "",
  "content": ""
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

  
