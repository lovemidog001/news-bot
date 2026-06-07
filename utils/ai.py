import os
import re
import json
import time
import requests

# =========================
# Prompt Builder
# =========================

def build_prompt(text):
    return f"""
你是一位充滿活力、說話接地氣的專業新聞編輯兼專欄作家，擅長從技術文章中挖掘最核心的價值。
現在要請你將一則英文新聞，轉譯並重編成台灣讀者會大感興趣、兼具深度與趣味的繁體中文報導。

請根據以下內容生成 JSON 格式。

撰寫規則:

1. score（品質評分）
- 0~100 分

2. takeaways
- 繁體中文
- 3 個重點

3. punchline
- 20 字內

4. title
- 15~30 字

5. summary
- 50~80 字

6. content
- HTML 格式
- 至少 400 字
- 包含兩個 <h2>
- 結尾必須有：
<h2>編輯悄悄話</h2>

重要規定:
- 嚴禁輸出英文段落
- 嚴禁捏造內容
- 只輸出 JSON

新聞內容：

{text}
"""


# =========================
# JSON Parse
# =========================

def safe_json_parse(output):

    if not output:
        return None

    try:
        output = output.strip()

        output = re.sub(
            r"```json",
            "",
            output,
            flags=re.IGNORECASE
        )

        output = re.sub(
            r"```",
            "",
            output
        )

        output = output.strip()

        return json.loads(output)

    except Exception:
        pass

    try:
        match = re.search(
            r"\{.*\}",
            output,
            re.DOTALL
        )

        if match:
            return json.loads(match.group())

    except Exception:
        pass

    return None


# =========================
# NVIDIA
# =========================

def call_nvidia(
    text,
    model="meta/llama-3.3-70b-instruct"
):
    api_key = os.getenv("NVIDIA_API_KEY")

    if not api_key:
        raise Exception("缺少 NVIDIA_API_KEY")

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
        "max_tokens": 2500
    }

    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=180
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


# =========================
# Gemini
# =========================

def call_gemini(
    text,
    model="gemini-2.5-flash"
):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise Exception("缺少 GEMINI_API_KEY")

    url = (
        f"https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": build_prompt(text)
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 2500
        }
    }

    response = requests.post(
        url,
        params={"key": api_key},
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    if "candidates" not in data:
        raise Exception(
            f"Gemini 回傳異常: {data}"
        )

    return (
        data["candidates"][0]
        ["content"]["parts"][0]["text"]
    )


# =========================
# DeepSeek
# =========================

def call_deepseek(
    text,
    model="deepseek-chat"
):
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise Exception("缺少 DEEPSEEK_API_KEY")

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
        "max_tokens": 2500
    }

    response = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers=headers,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    return (
        response.json()
        ["choices"][0]
        ["message"]["content"]
    )


# =========================
# Groq
# =========================

def call_groq(
    text,
    model="llama-3.3-70b-versatile"
):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise Exception("缺少 GROQ_API_KEY")

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
        "max_tokens": 2500
    }

    for attempt in range(3):

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )

        if response.status_code == 429:

            print(
                f"[Groq] Rate Limit "
                f"({attempt+1}/3)"
            )

            time.sleep(15)

            continue

        response.raise_for_status()

        return (
            response.json()
            ["choices"][0]
            ["message"]["content"]
        )

    raise Exception(
        "Groq Rate Limit 超過重試次數"
    )


# =========================
# Provider Map
# =========================

PROVIDER_MAP = {
    "gemini": call_gemini,
    "deepseek": call_deepseek,
    "nvidia": call_nvidia,
    "groq": call_groq,
}


# =========================
# AI Fallback
# =========================

def call_ai_with_fallback(
    text,
    fallback_chain=None
):

    if fallback_chain is None:
        fallback_chain = [
            "gemini",
            "deepseek",
            "nvidia",
            "groq"
        ]

    last_error = None

    for provider in fallback_chain:

        fn = PROVIDER_MAP.get(provider)

        if not fn:
            continue

        try:

            print(
                f"[Fallback] 嘗試 {provider}..."
            )

            result = fn(text)

            parsed = safe_json_parse(result)

            if not parsed:

                print(
                    f"[Fallback] "
                    f"{provider} JSON解析失敗"
                )

                continue

            print(
                f"[Fallback] "
                f"{provider} 成功"
            )

            return parsed, provider

        except Exception as e:

            print(
                f"[Fallback] "
                f"{provider} 失敗：{e}"
            )

            last_error = e

    raise Exception(
        f"所有 AI Provider 均失敗：{last_error}"
    )
