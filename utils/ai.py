import os
import requests


def build_prompt(text):
    return f"""
你是一位專業科技新聞編輯，必須用繁體中文撰寫完整的新聞報導。

請根據以下內容生成 JSON。

規則：

1. title（標題）
- 必須是繁體中文
- 15~30字
- 科技新聞風格，具體清楚
- 不要農場感、不要誇大
- 不可直接翻譯英文標題，要重新撰寫

2. summary（摘要）
- 必須是繁體中文
- 50~80字
- 說清楚新聞的核心重點、影響和意義

3. content（內文）
- 必須是繁體中文
- HTML 格式，使用 <p>、<h2>、<ul>、<li>、<strong> 等標籤
- 必須包含以下結構：
  * <h2>事件背景</h2><p>詳細說明這件事的來龍去脈，至少 80 字</p>
  * <h2>詳細內容</h2><p>深入分析事件細節、數據、相關人物或公司，至少 100 字</p>
  * <h2>影響與意義</h2><p>分析這件事對產業、使用者或市場的影響，至少 80 字</p>
  * <h2>未來展望</h2><p>說明後續可能的發展方向，至少 60 字</p>
- 總字數必須在 400 字以上
- 不可出現英文段落
- 不可使用「根據報導」、「據悉」等模糊開頭
- 內容要有深度，不要只是重複摘要

重要規定：
- 所有文字必須是繁體中文
- content 總字數不得少於 400 字
- 必須有 4 個 h2 小標題段落
- 文章要有新聞價值，不要流水帳

只輸出 JSON，不要 markdown，不要任何解釋。

格式：
{{
  "title": "",
  "summary": "",
  "content": ""
}}

新聞內容：
{text}
"""


# ── NVIDIA ──
def call_nvidia(text, model):
    api_key = os.getenv("NVIDIA_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "temperature": 0.6,
        "top_p": 0.9,
        "max_tokens": 2000
    }
    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers=headers, json=payload, timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ── Gemini ──
def call_gemini(text, model="gemini-2.0-flash"):
    import time
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": build_prompt(text)}]}],
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 2000}
    }
    for attempt in range(3):
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 429:
            wait = 10 * (attempt + 1)
            print(f"[Gemini] 429 rate limit，等待 {wait} 秒後重試...")
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    response.raise_for_status()


# ── DeepSeek ──
def call_deepseek(text, model="deepseek-chat"):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "temperature": 0.6,
        "max_tokens": 2000
    }
    response = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers=headers, json=payload, timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ── OpenAI ──
def call_openai(text, model="gpt-4o-mini"):
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "temperature": 0.6,
        "max_tokens": 2000
    }
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers, json=payload, timeout=60
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
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "temperature": 0.6,
        "max_tokens": 2000
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers, json=payload, timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ── Provider 對應表 ──
PROVIDER_MAP = {
    "nvidia":   call_nvidia,
    "gemini":   call_gemini,
    "deepseek": call_deepseek,
    "openai":   call_openai,
    "groq":     call_groq,
}


# ── ★ Fallback 核心：依序嘗試每個 Provider ──
def call_ai_with_fallback(text, fallback_chain, model):
    """
    fallback_chain: list，例如 ["nvidia", "gemini", "deepseek"]
    依序嘗試，成功就回傳結果，全部失敗則 raise Exception
    """
    last_error = None

    for provider in fallback_chain:
        fn = PROVIDER_MAP.get(provider)
        if not fn:
            print(f"[Fallback] 未知 provider：{provider}，跳過")
            continue

        try:
            print(f"[Fallback] 嘗試 {provider}...")
            result = fn(text, model) if provider == "nvidia" else fn(text)
            print(f"[Fallback] {provider} 成功")
            return result, provider

        except Exception as e:
            print(f"[Fallback] {provider} 失敗：{e}")
            last_error = e
            continue

    raise Exception(f"所有 AI Provider 均失敗，最後錯誤：{last_error}")
