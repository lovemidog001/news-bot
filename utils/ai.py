import os
import re
import json
import time
import logging
import requests

# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

# =========================================================
# Prompt 建構（已更新為網紅生活化 + H1 結構版）
# =========================================================

def build_prompt(text):

    text = text.strip()

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
- 資訊必須確實根據原文，不可憑空捏造事實，但在包裝與語氣上要活潑生動。
- 只輸出 JSON，不要 markdown（不要 ```json），不要任何前後文解釋。

【輸出格式】
{{
  "title": "",
  "summary": "",
  "content": ""
}}

新聞內容：
{text}
"""

# =========================================================
# JSON 處理公用函式
# =========================================================

def extract_json(text):
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group(0) if match else text.strip()

def repair_json(text):
    text = re.sub(r'(\{|,)\s*([a-zA-Z0-9_]+)\s*:', r'\1 "\2":', text)
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text

def validate_json(data):
    if not isinstance(data, dict):
        return False
    required_keys = ["title", "summary", "content"]
    for key in required_keys:
        if key not in data or not isinstance(data[key], str) or not data[key].strip():
            return False
    if len(data["content"]) < 300:
        return False
    return True

def safe_json_parse(output):
    cleaned = extract_json(output)
    try:
        parsed = json.loads(cleaned)
        if validate_json(parsed):
            return parsed
    except json.JSONDecodeError:
        pass
    try:
        repaired = repair_json(cleaned)
        parsed = json.loads(repaired)
        if validate_json(parsed):
            return parsed
    except Exception:
        pass
    return None

def self_heal_json(raw_output):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    logger.info("啟動 AI JSON 自我修復")
    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "你是 JSON 修復工具，只輸出合法 JSON，不要解釋。"},
            {"role": "user", "content": f"請修復以下 JSON：\n{raw_output}"}
        ],
        "temperature": 0
    }
    try:
        response = requests.post("[https://api.openai.com/v1/chat/completions](https://api.openai.com/v1/chat/completions)", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"]
        return safe_json_parse(result)
    except Exception:
        return None

# =========================================================
# AI API 各別呼叫端（維持你原有的基礎架構，優化模型配置）
# =========================================================

def call_nvidia(text, model):
    api_key = os.getenv("NVIDIA_API_KEY")
    # 防呆：如果主程式傳來不認得的 model，自動轉向 NVIDIA 的 Llama 模型
    if "gpt" in model or "llama" not in model:
        model = "meta/llama-3.1-70b-instruct"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "temperature": 0.6,
        "top_p": 0.9,
        "max_tokens": 2000
    }
    response = requests.post("[https://integrate.api.nvidia.com/v1/chat/completions](https://integrate.api.nvidia.com/v1/chat/completions)", headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def call_gemini(text, model="gemini-2.0-flash"):
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
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    response.raise_for_status()

def call_deepseek(text, model="deepseek-chat"):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "temperature": 0.6,
        "max_tokens": 2000
    }
    response = requests.post("[https://api.deepseek.com/chat/completions](https://api.deepseek.com/chat/completions)", headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def call_openai(text, model="gpt-4o-mini"):
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "temperature": 0.6,
        "max_tokens": 2000
    }
    response = requests.post("[https://api.openai.com/v1/chat/completions](https://api.openai.com/v1/chat/completions)", headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def call_groq(text, model="llama-3.3-70b-versatile"):
    api_key = os.getenv("GROQ_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": build_prompt(text)}],
        "temperature": 0.6,
        "max_tokens": 2000
    }
    response = requests.post("[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)", headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# =========================================================
# Provider 對應表
# =========================================================
PROVIDER_MAP = {
    "nvidia":   call_nvidia,
    "gemini":   call_gemini,
    "deepseek": call_deepseek,
    "openai":   call_openai,
    "groq":     call_groq,
}

# =========================================================
# Fallback 核心處理
# =========================================================
def call_ai_with_fallback(text, fallback_chain, model):
    last_error = None

    for provider in fallback_chain:
        fn = PROVIDER_MAP.get(provider)
        if not fn:
            logger.warning(f"[Fallback] 未知 provider：{provider}，跳過")
            continue

        try:
            logger.info(f"[Fallback] 嘗試使用 provider: {provider}")
            
            # 依據你原先的邏輯呼叫
            raw_result = fn(text, model) if provider == "nvidia" else fn(text)
            
            # 進行安全的 JSON 解析與驗證
            parsed = safe_json_parse(raw_result)
            
            if not parsed:
                # 嘗試自我修復
                parsed = self_heal_json(raw_result)
                
            if parsed:
                logger.info(f"[Fallback] {provider} 成功生成並通過 JSON 驗證")
                # 關鍵修正：回傳符合主程式預期的 2 個值 (JSON 字串, Provider 名稱)
                return json.dumps(parsed, ensure_ascii=False), provider
            else:
                logger.warning(f"[Fallback] {provider} 回傳格式非標準 JSON，嘗試下一家")
                last_error = "JSON 驗證與修復均失敗"

        except requests.HTTPError as e:
            logger.error(f"[Fallback] {provider} 網路錯誤：{e}")
            last_error = e
            if e.response.status_code == 429:
                time.sleep(15)  # 遇到429自動多冷卻15秒
        except Exception as e:
            logger.error(f"[Fallback] {provider} 發生錯誤：{e}")
            last_error = e
            continue

    raise Exception(f"所有 AI Provider 均失敗，最後錯誤：{last_error}")
