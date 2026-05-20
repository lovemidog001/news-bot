import os
import re
import json
import time
import hashlib
import logging
from typing import Optional, Dict, Tuple

import requests
from bs4 import BeautifulSoup

# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

# =========================================================
# Constants
# =========================================================

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

REQUEST_TIMEOUT = 60

REQUIRED_KEYS = ["title", "summary", "content"]

# =========================================================
# System Prompt
# =========================================================

SYSTEM_PROMPT = """
你是一位專業科技新聞編輯與台灣科技部落客。

請將英文科技新聞轉譯與重編為繁體中文台灣風格文章。

規則：

1. 必須使用繁體中文（台灣用語）
2. 禁止中國用語
3. 禁止農場標題
4. 禁止 AI 制式語氣
5. 禁止使用：
- 據悉
- 值得注意的是
- 總而言之
- 不難發現
- 由此可見

6. 禁止：
- emoji
- 過度浮誇
- 空泛內容
- 重複句型

7. 專有名詞可保留英文

8. 必須輸出合法 JSON

JSON 格式：

{
  "title": "",
  "summary": "",
  "content": ""
}

content 必須為 HTML。

HTML 必須包含：

<h2>這件事為什麼跟你有關？</h2>

<h2>拆解科技新趨勢</h2>

<h2>未來世界會變成怎樣？</h2>

<h2>編輯悄悄話</h2>
"""

# =========================================================
# Prompt Builder
# =========================================================

def build_user_prompt(text: str) -> str:
    text = text.strip()

    return f"""
請根據以下科技新聞內容，生成符合規範的 JSON。

要求：

1. title
- 15~30字
- 吸睛但不浮誇
- 使用 <h1>

2. summary
- 50~80字
- 點出影響力

3. content
- HTML 格式
- 400字以上
- 使用：
<p>
<h2>
<ul>
<li>
<strong>

新聞內容：

{text}
"""

# =========================================================
# Cache
# =========================================================

def get_cache_key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def load_cache(text: str) -> Optional[dict]:
    key = get_cache_key(text)
    path = os.path.join(CACHE_DIR, f"{key}.json")

    if os.path.exists(path):
        logger.info("使用 cache")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    return None

def save_cache(text: str, data: dict):
    key = get_cache_key(text)
    path = os.path.join(CACHE_DIR, f"{key}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =========================================================
# HTML Validation
# =========================================================

def validate_html(content: str) -> bool:
    try:
        soup = BeautifulSoup(content, "html.parser")

        required_h2 = [
            "這件事為什麼跟你有關？",
            "拆解科技新趨勢",
            "未來世界會變成怎樣？",
            "編輯悄悄話"
        ]

        h2_texts = [h.get_text(strip=True) for h in soup.find_all("h2")]

        for required in required_h2:
            if required not in h2_texts:
                logger.warning(f"缺少 H2: {required}")
                return False

        return True

    except Exception as e:
        logger.error(f"HTML 驗證失敗: {e}")
        return False

# =========================================================
# Schema Validation
# =========================================================

def validate_schema(data: dict) -> bool:

    if not isinstance(data, dict):
        return False

    for key in REQUIRED_KEYS:
        if key not in data:
            logger.warning(f"缺少欄位: {key}")
            return False

        if not isinstance(data[key], str):
            logger.warning(f"{key} 不是字串")
            return False

        if not data[key].strip():
            logger.warning(f"{key} 為空")
            return False

    if len(data["content"]) < 400:
        logger.warning("content 太短")
        return False

    if not validate_html(data["content"]):
        return False

    return True

# =========================================================
# JSON Cleaner
# =========================================================

def extract_json(text: str) -> str:

    # 移除 markdown code block
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)

    # 移除控制字元
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)

    # 抽取 JSON 區塊
    match = re.search(r'\{.*\}', text, re.DOTALL)

    if match:
        return match.group(0)

    return text

# =========================================================
# JSON Repair
# =========================================================

def repair_json(text: str) -> str:

    # 修復 key quote
    text = re.sub(
        r'(\{|,)\s*([a-zA-Z0-9_]+)\s*:',
        r'\1 "\2":',
        text
    )

    # 修復 trailing commas
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # 修復缺少逗號
    text = re.sub(
        r'"\s*\n\s*"',
        '",\n"',
        text
    )

    return text

# =========================================================
# Safe JSON Parse
# =========================================================

def safe_json_parse(output: str) -> Optional[dict]:

    cleaned = extract_json(output)

    try:
        return json.loads(cleaned)

    except json.JSONDecodeError as e:

        logger.warning(f"第一次 JSON 解析失敗: {e}")

        try:
            repaired = repair_json(cleaned)
            return json.loads(repaired)

        except json.JSONDecodeError as e2:
            logger.error(f"JSON 修復失敗: {e2}")
            return None

# =========================================================
# Self Healing JSON
# =========================================================

def self_heal_json(raw_output: str, api_key: str) -> Optional[dict]:

    logger.info("啟動 JSON 自我修復")

    prompt = f"""
請修復以下 JSON。

只輸出合法 JSON。
不要解釋。

JSON：

{raw_output}
"""

    try:

        payload = {
            "model": "gpt-4o-mini",
            "response_format": {"type": "json_object"},
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

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        result = response.json()["choices"][0]["message"]["content"]

        return safe_json_parse(result)

    except Exception as e:
        logger.error(f"JSON 自我修復失敗: {e}")
        return None

# =========================================================
# API Request
# =========================================================

def call_provider(
    provider: str,
    api_url: str,
    api_key: str,
    model: str,
    text: str
) -> str:

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": build_user_prompt(text)
            }
        ],
        "temperature": 0.6,
        "max_tokens": 2000
    }

    # OpenAI JSON mode
    if provider == "openai":
        payload["response_format"] = {
            "type": "json_object"
        }

    response = requests.post(
        api_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]

# =========================================================
# Providers
# =========================================================

def call_openai(text: str, model="gpt-4o-mini"):

    return call_provider(
        provider="openai",
        api_url="https://api.openai.com/v1/chat/completions",
        api_key=os.getenv("OPENAI_API_KEY"),
        model=model,
        text=text
    )

def call_groq(text: str, model="llama-3.3-70b-versatile"):

    return call_provider(
        provider="groq",
        api_url="https://api.groq.com/openai/v1/chat/completions",
        api_key=os.getenv("GROQ_API_KEY"),
        model=model,
        text=text
    )

def call_nvidia(text: str, model="gpt-4o-mini"):

    return call_provider(
        provider="nvidia",
        api_url="https://integrate.api.nvidia.com/v1/chat/completions",
        api_key=os.getenv("NVIDIA_API_KEY"),
        model=model,
        text=text
    )

# =========================================================
# Provider Map
# =========================================================

PROVIDER_MAP = {
    "openai": call_openai,
    "groq": call_groq,
    "nvidia": call_nvidia,
}

# =========================================================
# Main AI Function
# =========================================================

def call_ai_with_fallback_safe(
    text: str,
    fallback_chain=None,
    max_attempts=3
) -> Tuple[dict, str]:

    if fallback_chain is None:
        fallback_chain = [
            "groq",
            "openai",
            "nvidia"
        ]

    # =====================================================
    # Cache
    # =====================================================

    cached = load_cache(text)

    if cached:
        return cached, "cache"

    last_error = None

    # =====================================================
    # Provider Loop
    # =====================================================

    for provider in fallback_chain:

        logger.info(f"開始嘗試 Provider: {provider}")

        fn = PROVIDER_MAP.get(provider)

        if not fn:
            logger.warning(f"未知 Provider: {provider}")
            continue

        # =================================================
        # Retry Loop
        # =================================================

        for attempt in range(max_attempts):

            try:

                logger.info(
                    f"[{provider}] 第 {attempt+1}/{max_attempts} 次"
                )

                result = fn(text)

                parsed = safe_json_parse(result)

                # =========================================
                # JSON Repair AI
                # =========================================

                if not parsed:

                    logger.warning("JSON parsing 失敗")

                    openai_key = os.getenv("OPENAI_API_KEY")

                    if openai_key:

                        parsed = self_heal_json(
                            result,
                            openai_key
                        )

                # =========================================
                # Validation
                # =========================================

                if parsed and validate_schema(parsed):

                    logger.info(
                        f"[SUCCESS] 使用 Provider: {provider}"
                    )

                    save_cache(text, parsed)

                    return parsed, provider

                logger.warning("Schema validation 失敗")

            except requests.Timeout as e:

                logger.error(f"Timeout: {e}")
                last_error = e

            except requests.ConnectionError as e:

                logger.error(f"Connection Error: {e}")
                last_error = e

            except requests.HTTPError as e:

                logger.error(f"HTTP Error: {e}")
                last_error = e

            except Exception as e:

                logger.error(f"未知錯誤: {e}")
                last_error = e

            # =============================================
            # Backoff
            # =============================================

            sleep_time = 2 ** attempt

            logger.info(
                f"等待 {sleep_time} 秒後 retry..."
            )

            time.sleep(sleep_time)

        logger.warning(
            f"{provider} 已達最大重試次數"
        )

    raise Exception(
        f"所有 Provider 均失敗: {last_error}"
    )

# =========================================================
# Example Usage
# =========================================================

if __name__ == "__main__":

    sample_news = """
    Apple announced new AI features for iPhone users.
    The company says on-device AI will improve privacy
    and performance significantly.
    """

    try:

        result, provider = call_ai_with_fallback_safe(
            sample_news
        )

        print("\n========================")
        print("Provider:", provider)
        print("========================\n")

        print(json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ))

    except Exception as e:

        logger.error(f"執行失敗: {e}")
