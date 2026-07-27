#!/usr/bin/env python3
"""Generate and parse an outline with the extracted high-fidelity prompt."""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.parse
from pathlib import Path

from config import load_config, load_secret
from generate import compress_reference, mime_type, request_json

SKILL_ROOT = Path(__file__).resolve().parent.parent
OUTLINE_PROMPT = SKILL_ROOT / "assets" / "outline_prompt.txt"


def render_prompt(topic: str, image_count: int, product_count: int) -> str:
    template = OUTLINE_PROMPT.read_text(encoding="utf-8")
    prompt = template.replace("{topic}", topic) if "{topic}" in template else f"{template.rstrip()}\n\n用户的要求以及说明：\n{topic}"
    if image_count:
        mapping = "\n".join(f"- 第 {index} 张输入图片对应 @参考图{index}" for index in range(1, image_count + 1))
        prompt += f"\n\n用户提供了 {image_count} 张普通参考图。它们用于理解风格、人物、构图或场景：\n{mapping}"
    if product_count:
        start = image_count + 1
        mapping = "\n".join(
            f"- 第 {start + index - 1} 张输入图片对应 @产品图{index}" for index in range(1, product_count + 1)
        )
        prompt += f"""

用户还提供了 {product_count} 张产品图：
{mapping}

产品图是后续必须植入画面的真实商品，不是风格灵感。请在适合展示商品的页面内容中明确引用对应的 @产品图N，并写出自然陈列位置，例如桌面、台面、前景、背景以及左中右区域。不要设计复杂手持或遮挡关系。"""
    return prompt


def read_images(paths: list[str], max_kb: int = 220) -> list[bytes]:
    values = []
    for raw in paths or []:
        path = Path(raw).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"图片不存在：{path}")
        values.append(compress_reference(path.read_bytes(), max_kb))
    return values


def generate_google(prompt: str, images: list[bytes], config: dict, api_key: str) -> str:
    model = urllib.parse.quote(config.get("text_model", "gemini-3.5-flash"), safe="-._")
    base_url = config.get("text_base_url") or "https://generativelanguage.googleapis.com/v1beta"
    url = f"{base_url.rstrip('/')}/models/{model}:generateContent?key={urllib.parse.quote(api_key)}"
    parts = [
        {"inlineData": {"mimeType": mime_type(data), "data": base64.b64encode(data).decode("ascii")}}
        for data in images
    ]
    parts.append({"text": prompt})
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": config.get("text_temperature", 1.0),
            "maxOutputTokens": config.get("text_max_output_tokens", 8000),
        },
    }
    result = request_json(url, payload, {})
    text_parts = []
    for candidate in result.get("candidates") or []:
        for part in (candidate.get("content") or {}).get("parts") or []:
            if part.get("text"):
                text_parts.append(part["text"])
    if not text_parts:
        raise RuntimeError("文本模型没有返回大纲")
    return "".join(text_parts).strip()


def generate_openai(prompt: str, images: list[bytes], config: dict, api_key: str) -> str:
    content: str | list[dict] = prompt
    if images:
        content = [{"type": "text", "text": prompt}]
        for data in images:
            encoded = base64.b64encode(data).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type(data)};base64,{encoded}"}})
    payload = {
        "model": config.get("text_model"),
        "messages": [{"role": "user", "content": content}],
        "temperature": config.get("text_temperature", 1.0),
        "max_tokens": config.get("text_max_output_tokens", 8000),
        "stream": False,
    }
    base_url = config.get("text_base_url") or config.get("base_url") or "https://api.openai.com/v1"
    result = request_json(base_url.rstrip("/") + "/chat/completions", payload, {"Authorization": f"Bearer {api_key}"})
    try:
        return str(result["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("文本服务响应中没有大纲") from exc


def parse_outline(raw: str) -> list[dict]:
    chunks = re.split(r"<page>", raw, flags=re.IGNORECASE) if "<page>" in raw.lower() else raw.split("---")
    pages = []
    for chunk in chunks:
        content = chunk.strip()
        if not content:
            continue
        match = re.match(r"\[(\S+)\]", content)
        label = match.group(1) if match else "内容"
        page_type = {"封面": "cover", "内容": "content", "总结": "summary"}.get(label, "content")
        pages.append({"index": len(pages) + 1, "type": page_type, "content": content})
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description="使用原始图文提示体系生成详细大纲")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--topic")
    group.add_argument("--topic-file")
    parser.add_argument("--image", action="append", default=[])
    parser.add_argument("--product-image", action="append", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    topic = args.topic or Path(args.topic_file).read_text(encoding="utf-8")
    if not topic.strip():
        print("主题不能为空")
        return 2
    normal = read_images(args.image, 220)
    products = read_images(args.product_image, 500)
    config = load_config()
    provider = config.get("text_provider") or config.get("provider")
    credential = config.get("text_credential_name") or config.get("credential_name") or provider
    api_key = load_secret(credential)
    if not api_key:
        print("没有找到文本模型 API Key，请运行 python3 scripts/setup.py")
        return 2
    prompt = render_prompt(topic.strip(), len(normal), len(products))
    if provider == "google":
        raw = generate_google(prompt, [*normal, *products], config, api_key)
    elif provider in {"openai", "openai_compatible"}:
        raw = generate_openai(prompt, [*normal, *products], config, api_key)
    else:
        print(f"当前 provider 不支持独立大纲生成：{provider}")
        return 2
    pages = parse_outline(raw)
    if not pages:
        print("未能从模型响应中解析出页面")
        return 1
    result = {"success": True, "topic": topic.strip(), "outline": raw, "pages": pages, "has_images": bool(normal or products)}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ 大纲生成完成，共 {len(pages)} 页：{output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
