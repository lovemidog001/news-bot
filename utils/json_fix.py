import json
import re


def repair_json(text):

    text = text.strip()

    text = text.replace("```json", "")
    text = text.replace("```", "")

    match = re.search(r'\\{.*\\}', text, re.DOTALL)

    if match:
        text = match.group(0)

    text = re.sub(r',\\s*}', '}', text)
    text = re.sub(r',\\s*]', ']', text)

    return json.loads(text)
