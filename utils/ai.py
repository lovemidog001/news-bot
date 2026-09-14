import os
import re
import json
import time
import requests
from typing import Optional


# ===== Retry 設定 =====
MAX_RETRIES = 3
BASE_DELAY = 2  # 秒

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
    """NVIDIA Nemotron / Llama models via NVIDIA API"""
    return _call_with_retry(
        provider="nvidia",
        url="https://integrate.api.nvidia.com/v1/chat/completions",
        headers_factory=lambda key: {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        payload_factory=lambda m: {
            "model": m,
            "messages": [{"role": "user", "content": build_prompt(text)}],
            "temperature": 0.6,
            "top_p": 0.9,
            "max_tokens": 2000
        },
        model=model,
        api_key_env="NVIDIA_API_KEY",
        response_parser=lambda r: r.json()["choices"][0]["message"]["content"]
    )


# ── Gemini ──
def call_gemini(text, model="gemini-1.5-flash-002"):
    """Google Gemini API with retry"""
    def _gemini_headers(key):
        return {"Content-Type": "application/json"}
    
    def _gemini_payload(m):
        return {
            "contents": [{"parts": [{"text": build_prompt(text)}]}],
            "generationConfig": {
                "temperature": 0.6,
                "maxOutputTokens": 2000
            }
        }
    
    def _gemini_parser(r):
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    
    return _call_with_retry(
        provider="gemini",
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={{api_key}}",
        headers_factory=_gemini_headers,
        payload_factory=_gemini_payload,
        model=model,
        api_key_env="GEMINI_API_KEY",
        response_parser=_gemini_parser,
        inject_key_in_url=True
    )


# ── Groq ──
def call_groq(text, model="llama-3.3-70b-versatile"):
    """Groq API with retry"""
    return _call_with_retry(
        provider="groq",
        url="https://api.groq.com/openai/v1/chat/completions",
        headers_factory=lambda key: {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        payload_factory=lambda m: {
            "model": m,
            "messages": [{"role": "user", "content": build_prompt(text)}],
            "temperature": 0.6,
            "max_tokens": 2000
        },
        model=model,
        api_key_env="GROQ_API_KEY",
        response_parser=lambda r: r.json()["choices"][0]["message"]["content"]
    )


# ── Agnes AI ──
def call_agnes(text, model="agnes-2.0-flash"):
    """Agnes AI API with retry"""
    return _call_with_retry(
        provider="agnes",
        url="https://apihub.agnes-ai.com/v1/chat/completions",
        headers_factory=lambda key: {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        payload_factory=lambda m: {
            "model": m,
            "messages": [{"role": "user", "content": build_prompt(text)}],
            "temperature": 0.3,
            "max_tokens": 2000
        },
        model=model,
        api_key_env="AGNES_API_KEY",
        response_parser=lambda r: r.json()["choices"][0]["message"]["content"]
    )


# ===== 通用重試邏輯 =====
def _call_with_retry(
    provider: str,
    url: str,
    headers_factory,
    payload_factory,
    model: str,
    api_key_env: str,
    response_parser,
    inject_key_in_url: bool = False
):
    """
    通用的帶重試機制 API 調用
    - 支援指數退避重試
    - 自動處理 429 (rate limit), 5xx (server error)
    - 401/403/404 不重試 (認證/端點問題)
    """
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise ValueError(f"{api_key_env} 環境變數未設定")

    # 處理 URL 中的 API key 注入 (Gemini 用)
    final_url = url
    if inject_key_in_url:
        final_url = url.format(api_key=api_key)

    headers = headers_factory(api_key)
    payload = payload_factory(model)

    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                final_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            # 不重試的錯誤碼
            if response.status_code in (401, 403, 404):
                response.raise_for_status()
            
            # 可重試的錯誤碼
            if response.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{response.status_code}: {response.text}", response=response)
            
            response.raise_for_status()
            return response_parser(response)
            
        except requests.exceptions.Timeout:
            last_error = Exception(f"請求超時 (60s)")
        except requests.exceptions.ConnectionError as e:
            last_error = Exception(f"連線錯誤: {e}")
        except requests.exceptions.HTTPError as e:
            last_error = e
            if e.response is not None and e.response.status_code not in (429, 500, 502, 503, 504):
                raise
        except Exception as e:
            last_error = e
        
        if attempt < MAX_RETRIES - 1:
            delay = BASE_DELAY * (2 ** attempt)
            print(f"[Fallback] {provider} 第 {attempt + 1} 次失敗: {last_error}，{delay}s 後重試...")
            time.sleep(delay)
        else:
            print(f"[Fallback] {provider} 重試 {MAX_RETRIES} 次均失敗: {last_error}")
    
    raise last_error or Exception(f"{provider} 調用失敗")


# ── Provider 對應表 ──
PROVIDER_MAP = {
    "agnes": call_agnes,
    "groq": call_groq,
    "nvidia": call_nvidia,
    "gemini": call_gemini,
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
    fallback_chain=["agnes", "groq", "nvidia", "gemini"],
    models=None
):
    """
    嘗試多個 AI Provider 直到成功
    :param text: 輸入文字
    :param fallback_chain: provider 名稱列表
    :param models: dict，對應 provider -> model name
    """
    last_error = None

    for provider in fallback_chain:

        fn = PROVIDER_MAP.get(provider)

        if not fn:
            continue

        # 取得該 provider 的 model 設定
        model = models.get(provider) if models else None

        try:

            print(f"[Fallback] 嘗試 {provider} (model: {model or 'default'})...")

            result = fn(text, model=model) if model else fn(text)

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
