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
        "max_tokens": 800
    }
    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers=headers, json=payload, timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ── Gemini ──
def call_gemini(text, model="gemini-2.0-flash"):
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": build_prompt(text)}]}],
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 800}
    }
    response = requests.post(url, json=payload, timeout=60)
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
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "temperature": 0.6,
        "max_tokens": 800
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
        "max_tokens": 800
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
        "max_tokens": 800
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
            # NVIDIA 用 config 的 model，其他用各自預設
            result = fn(text, model) if provider == "nvidia" else fn(text)
            print(f"[Fallback] {provider} 成功")
            return result, provider

        except Exception as e:
            print(f"[Fallback] {provider} 失敗：{e}")
            last_error = e
            continue

    raise Exception(f"所有 AI Provider 均失敗，最後錯誤：{last_error}")
