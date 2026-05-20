import os
import requests



# =========================================================
# Prompt 建構（已更新為網網紅生活化 + H1 結構版）
# =========================================================

def build_prompt(text):
    # 註解：在 f-string 中，純文字的「{」和「}」必須寫成「{{」和「}}」來進行轉義。
    # 註解：只有最底部的 {text} 需要保持單個大括號，用來帶入 Python 變數。
    return f"""
你是一位充滿活力、說話接地氣的專業科技網紅兼新聞編輯。現在要請你將一則英文科技新聞，轉譯並重編成台灣讀者會大感興趣、兼具深度與趣味的繁體中文報導。

請根據以下內容生成 JSON 格式。

【撰寫規則】

1. title（標題）
- 必須是繁體中文（台灣習慣用語，例如：品質、優化、螢幕，而非質量、優化、屏幕）。
- 15~30字。
- 必須吸睛、帶有懸念或痛點（例如：別再盲目跟風！、這項新技術可能改變你的生活...）。
- 不要農場感、不要過度誇大，要重新撰寫，絕對不可直接翻譯英文標題。
- 不要問句結尾。

2. summary（摘要）
- 必須是繁體中文，50~80字。
- 一針見血指出新聞核心、這件事會造成什麼巨大改變，讓讀者3秒內看懂影響力。

3. content（內文）
- 必須是繁體中文，使用 HTML 格式（包含 <h1>、<h2>、<p>、<ul>、<li>、<strong> 標籤）。
- 總字數必須在 400 字以上（不含 H1 與 H2 標籤）。
- 語氣要像科技部落客在跟朋友聊天，生活化、口語化，但分析要到位。
- 不可使用「根據報導」、「據悉」等死板開頭。
- 【SEO 重要結構】內文最開頭必須是 <h1> 標籤（內容與 title 完全一致），隨後必須嚴格包含以下四個 <h2> 結構（請直接使用以下指定的小標題文字）：
  
  <h1>（這裡直接填入上方生成的 title 內容）</h1>

  * <h2>這件事為什麼跟你有關？</h2>
    <p>說明事件背景與來龍去脈。請從讀者視角或生活痛點切入，解釋為什麼這則新聞值得關注，至少 80 字。</p>
    
  * <h2>拆解科技新趨勢</h2>
    <p>深入分析事件細節、技術數據、相關人物或公司舉動，至少 100 字。</p>
    
  * <h2>未來世界會變成怎樣？</h2>
    <p>核心重點！深入分析這項科技對產業、市場，或大眾未來生活會帶來怎樣的重大改變與影響，至少 80 字。</p>
    
  * <h2>編輯悄悄話</h2>
    <p>生活趣味口語結論！用最接地氣、幽默、像朋友聊天的口吻，總結這場科技變革，給讀者一個有趣的反思，至少 60 字。</p>

【禁止】
- emoji
- 中國用語（如：質量、優化、屏幕、計算機、智能）
- AI 制式語氣
- 「值得注意的是」
- 「總而言之」
- 「據悉」

【重要規定】
- 嚴禁出現英文段落，專有名詞（如 AI, Apple, Google, Meta）除外。
- 資訊必須確實根據原文，不可憑空捏造事实，但在包裝與語氣上要活潑生動。
- 只輸出 JSON，不要 markdown（不要 ```json），不要任何前後文解釋。

【輸出格式】
{{{{
  "title": "",
  "summary": "",
  "content": ""
}}}}

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
        "[https://integrate.api.nvidia.com/v1/chat/completions](https://integrate.api.nvidia.com/v1/chat/completions)",
        headers=headers, json=payload, timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ── Gemini ──
def call_gemini(text, model="gemini-2.0-flash"):
    import time
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){model}:generateContent?key={api_key}"
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
        "[https://api.deepseek.com/chat/completions](https://api.deepseek.com/chat/completions)",
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
        "[https://api.openai.com/v1/chat/completions](https://api.openai.com/v1/chat/completions)",
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
        "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)",
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
