import os
import requests


def build_prompt(text):
    return f"""
你是一位幽默、說話接地氣的科技趨勢觀察家（科技線網網紅編輯）。
請將提供的生硬科技素材，轉化為「前半段客觀摘錄、後半段趣味口語解析」的黃金比例報導，用繁體中文撰寫，並輸出為 JSON。

【撰寫指南】
1. 語氣調配：
- 「新聞摘錄」部分：請保持客觀、清晰、重點明確，不要流水帳。
- 「趣味解析」部分：徹底丟掉官腔！用生活化、像在跟朋友聊天、帶點吐槽或讚嘆的口語，點出這件事的真正亮點或槽點。

2. JSON 欄位規則：

- title（標題）：
  * 必須是繁體中文，15~30字。
  * 要吸睛、直擊痛點、有話題性，但拒絕低俗的內容農場感。
  * 【鐵律】不可直接翻譯英文標題，必須根據新聞內文「重新撰寫」出符合中文閱讀習慣的吸睛標題。

- summary（摘要）：
  * 必須是繁體中文，50~80字。
  * 【鐵律】必須清清楚楚地說清楚這則新聞的「核心重點」、「影響」和「意義」。

- content（內文）：
  * 必須是 HTML 格式，只能使用 <p>、<h2>、<ul>、<li>、<strong> 標籤。
  * 總字數必須在 300 字以上。
  * 必須嚴格包含以下 4 個 h2 結構（前兩段為客觀摘錄，後兩段為趣味解析）：
    * <h2>📰 重點新聞摘錄</h2><p>（客觀說明這件事的來龍去脈與核心事實，至少 50 字）</p>
    * <h2>🔍 關鍵細節與數據</h2><p>（列出事件的技術規格、數據或重要人物發言，至少 50 字，可用 ul/li 條列）</p>
    * <h2>💬 編輯白話文瞎聊</h2><p>（切換為趣味口語！用最直白、有梗的話解釋這到底意味著什麼，至少 50 字）</p>
    * <h2>💡 這對我們有啥影響？</h2><p>（用生活化的角度預測未來的改變或吃瓜方向，至少 40 字）</p>

【重要規定】
- 全文所有文字必須是繁體中文（專有名詞除外）。
- 嚴格遵守 HTML 標籤結構與各段落字數要求。
- 只輸出 JSON 格式本身，絕對不要包含 markdown 的 ```json 讀取框，也不要任何前後解釋。

【輸出格式】
{{
  "title": "",
  "summary": "",
  "content": ""
}}

【新聞內容】
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
