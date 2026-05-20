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
# Prompt 建構
# =========================================================

def build_prompt(text):
    return f"""
你是一位充滿活力、說話接地氣的專業科技網紅兼新聞編輯。現在要請你將一則英文科技新聞，轉譯並重編成台灣讀者會大感興趣、兼具深度與趣味的繁體中文報導。

請根據以下內容生成 JSON 格式。

【撰寫規則】

1. title（標題）
- 必須是繁體中文（台灣習慣用語，例如：品質、優化、螢幕，而非質量、優化、屏幕）。
- 15~30字。
- 必須吸睛、帶有懸念或痛點（例如：別再盲目跟風！、這項新技術可能改變你的生活...）。
- 不要農場感、不要過度誇大，要重新撰寫，絕對不可直接翻譯英文標題。

2. summary（摘要）
- 必須是繁體中文，50~80字。
- 一針見血指出新聞核心、這件事會造成什麼巨大改變，讓讀者3秒內看懂影響力。

3. content（內文）
- 必須是繁體中文，使用 HTML 格式（包含 <h1>、<h2>、<p>、<ul>、<li>、<strong> 標籤）。
- 總字數必須在 400 字以上（不含 H1 與 H2 標籤）。
- 語氣要像科技部落客在跟朋友聊天，生活化、口語化，但分析要到位。
- 不可使用「根據報導」、「據悉」等死板開頭。
- 【SEO 重要結構】內文最開頭必須是 <h1> 標籤（內容與 title 完全一致），隨後必須嚴格包含以下四個 <h2> 結構：
  
  <h1>（這裡直接填入上方生成的 title 內容）</h1>

  * <h2>這件事為什麼跟你有關？</h2>
    <p>說明事件背景與來龍去脈。請從讀者視角或生活痛點切入，解釋為什麼這則新聞值得關注，至少 80 字。</p>
    
  * <h2>拆解科技新趨勢</h2>
    <p>深入分析事件細節、技術數據、相關人物或公司舉動，至少 100 字。</p>
    
  * <h2>未來世界會變成怎樣？</h2>
    <p>核心重點！深入分析這項科技對產業、市場，或大眾未來生活會帶來怎樣的重大改變與影響，至少 80 字。</p>
    
  * <h2>編輯悄悄話</h2>
    <p>生活趣味口語結論！用最接地氣、幽默、像朋友聊天的口吻，總結這場科技變革，給讀者一個有趣的反思，至少 60 字。</p>

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
# JSON 抽取
# =========================================================

def extract_json(text):

    # 移除 markdown code block
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)

    # 移除控制字元
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)

    # 擷取 JSON 區塊
    match = re.search(r'\{.*\}', text, re.DOTALL)

    if match:
        return match.group(0)

    return text.strip()

# =========================================================
# JSON 修復
# =========================================================

def repair_json(text):

    # 修復 key quote
    text = re.sub(
        r'(\{|,)\s*([a-zA-Z0-9_]+)\s*:',
        r'\1 "\2":',
        text
    )

    # 修復 trailing commas
    text = re.sub(
        r',\s*([}\]])',
        r'\1',
        text
    )

    return text

# =========================================================
# JSON 驗證
# =========================================================

def validate_json(data):

    if not isinstance(data, dict):
        return False

    required_keys = [
        "title",
        "summary",
        "content"
    ]

    for key in required_keys:

        if key not in data:
            logger.warning(f"缺少欄位: {key}")
            return False

        if not isinstance(data[key], str):
            logger.warning(f"{key} 不是字串")
            return False

        if not data[key].strip():
            logger.warning(f"{key} 為空")
            return False

    if len(data["content"]) < 300:
        logger.warning("content 太短")
        return False

    return True

# =========================================================
# 安全 JSON Parse
# =========================================================

def safe_json_parse(output):

    cleaned = extract_json(output)

    try:

        parsed = json.loads(cleaned)

        if validate_json(parsed):
            return parsed

    except json.JSONDecodeError as e:

        logger.warning(f"第一次 JSON parse 失敗: {e}")

    # 嘗試修復
    try:

        repaired = repair_json(cleaned)

        parsed = json.loads(repaired)

        if validate_json(parsed):
            logger.info("JSON 修復成功")
            return parsed

    except Exception as e:

        logger.error(f"JSON 修復失敗: {e}")

    return None

# =========================================================
# JSON 自我修復
# =========================================================

def self_heal_json(raw_output):

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    logger.info("啟動 AI JSON 自我修復")

    prompt = f"""
請修復以下 JSON。

只輸出合法 JSON。
不要解釋。

JSON：

{raw_output}
"""

    payload = {
        "model": "gpt-4o-mini",
        "response_format": {
            "type": "json_object"
        },
        "messages": [
            {
                "role": "system",
                "content": "你是 JSON 修復工具。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0
    }

    try:

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()["choices"][0]["message"]["content"]

        parsed = safe_json_parse(result)

        if parsed:
            return json.dumps(
                parsed,
                ensure_ascii=False
            )

    except Exception as e:

        logger.error(f"JSON 自我修復失敗: {e}")

    return None

# =========================================================
# Provider Calls (這裡修正了預設 Model 名稱，並統一接口不帶 model 參數)
# =========================================================

def call_nvidia(text):

    api_key = os.getenv("NVIDIA_API_KEY")
    
    # 修正：NVIDIA 認不得 gpt-4o-mini，改成 NVIDIA 支援的標準 Llama 模型
    model = "meta/llama-3.1-70b-instruct"

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

def call_groq(text):

    api_key = os.getenv("GROQ_API_KEY")
    model = "llama-3.3-70b-versatile"

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

def call_openai(text):

    api_key = os.getenv("OPENAI_API_KEY")
    model = "gpt-4o-mini"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "response_format": {
            "type": "json_object"
        },
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
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]

# =========================================================
# Provider Map
# =========================================================

PROVIDER_MAP = {
    "nvidia": call_nvidia,
    "groq": call_groq,
    "openai": call_openai,
}

# =========================================================
# Fallback
# =========================================================

def call_ai_with_fallback(
    text,
    fallback_chain=["groq", "openai", "nvidia"],
    max_attempts=3
):

    last_error = None

    for provider in fallback_chain:

        fn = PROVIDER_MAP.get(provider)

        if not fn:
            logger.warning(f"未知 provider: {provider}")
            continue

        logger.info(f"開始使用 provider: {provider}")

        for attempt in range(max_attempts):

            try:

                logger.info(
                    f"{provider} 第 {attempt+1}/{max_attempts} 次"
                )

                # 修正：移除傳遞 model 參數，接口完全統一為 fn(text)
                result = fn(text)

                # 驗證 JSON
                parsed = safe_json_parse(result)

                # 如果 JSON OK
                if parsed:

                    logger.info(
                        f"{provider} JSON 驗證成功"
                    )

                    return json.dumps(
                        parsed,
                        ensure_ascii=False
                    )

                logger.warning(
                    f"{provider} JSON 驗證失敗"
                )

                # AI 自我修復
                healed = self_heal_json(result)

                if healed:

                    logger.info(
                        "AI JSON 自我修復成功"
                    )

                    return healed

            except requests.Timeout as e:
                logger.error(f"Timeout: {e}")
                last_error = e

            except requests.ConnectionError as e:
                logger.error(f"ConnectionError: {e}")
                last_error = e

            except requests.HTTPError as e:
                logger.error(f"HTTPError: {e}")
                last_error = e
                
                # 優化：如果遇到 429 Too Many Requests，拉長等待時間讓 API 冷卻
                if e.response.status_code == 429:
                    logger.warning("觸發 429 頻率限制，延長等待時間...")
                    time.sleep(15)

            except Exception as e:
                logger.error(f"未知錯誤: {e}")
                last_error = e

            # 指數退避（如果遇到 429 則底數放大，避免重試過快）
            sleep_time = (2 ** attempt) * 3
            logger.info(f"等待 {sleep_time} 秒後重試")
            time.sleep(sleep_time)

        logger.warning(
            f"{provider} 已達最大重試次數"
        )

    raise Exception(
        f"所有 AI Provider 均失敗: {last_error}"
    )
