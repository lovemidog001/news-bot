import os
import re
import json
import time
import requests

def build_prompt(text):
    return f"""
你是一位頂尖的社群內容策略師與新聞編輯，擅長將生硬的資訊轉化為具備「爆款潛力」的社群內容。
你的目標是根據提供的新聞內容，生成一份兼具深度、情緒價值與高度傳播力的報導。

### 撰寫策略指導（核心邏輯）：
1. **爆款標題公式**：從以下三種邏輯中擇一應用：
   - [反直覺型]：挑戰常識，引發「為什麼會這樣？」的好奇。
   - [損失厭惡型]：強調如果不看會錯過什麼、或是如何避坑。
   - [高價值清單型]：強調實用性，讓人想先收藏。
2. **情緒價值**：文章中必須包含情緒起伏，使用接地氣的台灣習慣用語，避免官腔官調。
3. **敘事意圖**：不要只是摘要，要提供「洞察」。告訴讀者這件事對他們的具體影響是什麼。

### 格式要求：
請輸出純 JSON 格式，包含以下欄位：

1. **score**: (0-100) 綜合新聞價值與話題性評分。
2. **title**: 使用爆款公式生成的標題（15-30字，嚴禁農場文風格）。
3. **summary**: 一針見血的摘要（50-80字），要讓讀者感到「這與我有關」。
4. **takeaways**: 3 個精煉的核心觀點（陣列格式）。
5. **punchline**: 文章中最精闢、最具轉發價值的一句話（20字內）。
6. **content**: 深度報導內容。使用 HTML 格式（<p>、<h2>、<ul>、<strong>）。
   - 必須包含 2 個 <h2>。
   - 結尾必須是 <h2>編輯悄悄話</h2>，用幽默、毒舌或感性的口吻總結。
7. **social_posts**: (物件格式) 針對不同平台生成的發佈草稿：
   - **threads**: 口語化、多換行、少標籤、強調個人觀點或共鳴。
   - **facebook**: 專業感中帶有互動導引，適合長文分享。
   - **viral_hook**: 一句專門用來在社群媒體開頭「抓眼球」的話。

重要規定：
- 全文使用繁體中文（台灣）。
- 輸出必須是合法 JSON，不含 Markdown 程式碼區塊標籤。

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
        "messages": [{"role": "user", "content": build_prompt(text)}],
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
    if not api_key:
        raise Exception("缺少 GEMINI_API_KEY 環境變數")
    
    # 採用官方推薦的 v1beta 格式
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": build_prompt(text)}]}],
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
        "messages": [{"role": "user", "content": build_prompt(text)}],
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
        "messages": [{"role": "user", "content": build_prompt(text)}],
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
def call_ai_with_fallback(text, fallback_chain=["deepseek", "gemini", "groq", "nvidia"]):
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
