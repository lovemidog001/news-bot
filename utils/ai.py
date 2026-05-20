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

    text = text.strip()

    return f"""
你是一位充滿活力、說話接地氣的專業科技網紅兼新聞編輯。

請將英文科技新聞轉譯並重編為：

- 台灣繁體中文
- 專業但生活化
- 適合科技媒體網站

請根據以下內容生成 JSON 格式。

【規則】

1. title
- 必須使用 <h1>
- 15~30字
- 台灣繁體中文
- 吸睛但不浮誇
- 禁止農場標題
- 不要問句結尾

2. summary
- 50~80字
- 點出核心影響

3. content
- HTML 格式
- 必須包含：
<p>
<h2>
<ul>
<li>
<strong>

- 字數 400 字以上

- 必須包含以下 H2：

<h2>這件事為什麼跟你有關？</h2>

<h2>拆解科技新趨勢</h2>

<h2>未來世界會變成怎樣？</h2>

<h2>編輯悄悄話</h2>

【禁止】

- emoji
- 中國用語
- AI 制式語氣
- 「值得注意的是」
- 「總而言之」
- 「據悉」

【輸出格式】

{{
  "title": "",
  "summary": "",
  "content": ""
}}

只輸出 JSON。

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
