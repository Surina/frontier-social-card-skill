#!/usr/bin/env python3
"""Generate Xiaohongshu publication copy with the extracted content prompt."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

from config import load_config, load_secret
from generate import request_json

SKILL_ROOT = Path(__file__).resolve().parent.parent
CONTENT_PROMPT = SKILL_ROOT / "assets" / "content_prompt.txt"


def split_characters(value: str) -> list[str]:
    clusters: list[str] = []
    current = ""
    join_next = False
    for char in value or "":
        category = unicodedata.category(char)
        if not current:
            current = char
        elif char == "\u200d" or join_next or category.startswith("M") or "\ufe00" <= char <= "\ufe0f":
            current += char
            join_next = char == "\u200d"
        else:
            clusters.append(current)
            current = char
            join_next = False
    if current:
        clusters.append(current)
    return clusters


def normalize_title(value: str, maximum: float = 20) -> str:
    total = 0.0
    result = ""
    for item in split_characters(str(value or "").strip()):
        if any("\U0001F000" <= char <= "\U0001FAFF" or "\u2700" <= char <= "\u27BF" or "\u2600" <= char <= "\u26FF" for char in item):
            weight = 2
        elif re.fullmatch(r"[A-Za-z]", item):
            weight = 0.5
        else:
            weight = 1
        if total + weight > maximum:
            break
        total += weight
        result += item
    return result.strip()


def parse_json(value: str) -> dict:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", value)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    start, end = value.find("{"), value.rfind("}")
    if start >= 0 and end > start:
        return json.loads(value[start:end + 1])
    raise ValueError("文本模型返回的内容不是有效 JSON")


def generate_text(prompt: str, config: dict, api_key: str) -> str:
    provider = config.get("text_provider") or config.get("provider")
    if provider == "google":
        model = config.get("text_model", "gemini-3.5-flash")
        base_url = config.get("text_base_url") or "https://generativelanguage.googleapis.com/v1beta"
        url = f"{base_url.rstrip('/')}/models/{urllib.parse.quote(str(model), safe='-._')}:generateContent?key={urllib.parse.quote(api_key)}"
        result = request_json(url, {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": config.get("text_temperature", 1.0),
                "maxOutputTokens": config.get("text_max_output_tokens", 4000),
            },
        }, {})
        return "".join(
            part.get("text", "")
            for candidate in result.get("candidates") or []
            for part in (candidate.get("content") or {}).get("parts") or []
        ).strip()
    if provider in {"openai", "openai_compatible"}:
        base_url = config.get("text_base_url") or config.get("base_url")
        result = request_json(base_url.rstrip("/") + "/chat/completions", {
            "model": config.get("text_model"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.get("text_temperature", 1.0),
            "max_tokens": config.get("text_max_output_tokens", 4000),
            "stream": False,
        }, {"Authorization": f"Bearer {api_key}"})
        return str(result["choices"][0]["message"]["content"]).strip()
    raise ValueError(f"不支持的文本 provider：{provider}")


def main() -> int:
    parser = argparse.ArgumentParser(description="使用原始内容提示体系生成发布文案")
    parser.add_argument("--outline", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    outline_data = json.loads(Path(args.outline).read_text(encoding="utf-8"))
    prompt = CONTENT_PROMPT.read_text(encoding="utf-8").format(
        topic=str(outline_data.get("topic") or ""),
        outline=str(outline_data.get("outline") or ""),
    )
    config = load_config()
    credential = config.get("text_credential_name") or config.get("credential_name")
    api_key = load_secret(credential)
    if not api_key:
        print("没有找到文本模型 API Key，请运行 python3 scripts/setup.py")
        return 2
    content = parse_json(generate_text(prompt, config, api_key))
    titles = content.get("titles") or []
    if isinstance(titles, str):
        titles = [titles]
    tags = content.get("tags") or []
    if isinstance(tags, str):
        tags = [item.strip() for item in tags.split(",")]
    result = {
        "success": True,
        "titles": [title for title in (normalize_title(item) for item in titles) if title],
        "copywriting": content.get("copywriting") or "",
        "tags": tags,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ 发布文案生成完成：{output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
