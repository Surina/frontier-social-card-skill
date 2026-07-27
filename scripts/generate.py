#!/usr/bin/env python3
"""Standalone high-fidelity social-card image pipeline."""

from __future__ import annotations

import argparse
import base64
import io
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from config import load_config, load_secret
from validate_plan import validate

SKILL_ROOT = Path(__file__).resolve().parent.parent
PROMPT_TEMPLATE = SKILL_ROOT / "assets" / "image_prompt.txt"
PRODUCT_INSTRUCTION = """【产品图强制规则】
- @产品图N 是用户上传、需要植入画面的真实商品素材，不是风格参考图。
- 必须使用对应 @产品图N 中的商品，不得替换成相似商品，不得自行设计新包装。
- 尽量保持商品包装、颜色、形状、品牌识别元素和可辨识文字与输入产品图一致。
- 允许为自然融入场景调整背景、光影、比例和透视，但不要弱化、遮挡或重绘商品的核心识别特征。
- 首版仅使用自然陈列位置，例如桌面、台面、前景、背景及左中右区域，不要设计复杂手持或遮挡关系。"""


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def request_json(url: str, payload: dict, headers: dict, timeout: int = 300) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl_context()) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1500]
        raise RuntimeError(f"图片服务返回 HTTP {exc.code}：{detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"无法连接图片服务：{exc.reason}") from exc


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "frontier-social-card/2.0"})
    with urllib.request.urlopen(request, timeout=300, context=ssl_context()) as response:
        return response.read()


def mime_type(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return "image/webp"
    return "image/png"


def extension(data: bytes) -> str:
    return {"image/jpeg": ".jpg", "image/webp": ".webp"}.get(mime_type(data), ".png")


def compress_reference(data: bytes, max_kb: int = 220) -> bytes:
    if len(data) <= max_kb * 1024:
        return data
    try:
        from PIL import Image  # type: ignore

        image = Image.open(io.BytesIO(data))
        image.load()
        image.thumbnail((1600, 1600))
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        for quality in (88, 78, 68, 58):
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True)
            if len(output.getvalue()) <= max_kb * 1024:
                return output.getvalue()
        return output.getvalue()
    except Exception:
        return data


def page_content(page: dict) -> str:
    body = page.get("body") or []
    if isinstance(body, str):
        body = [body]
    lines = [f"标题：{page.get('headline', '')}"]
    if body:
        lines.append("正文：")
        lines.extend(f"- {item}" for item in body)
    if page.get("visual"):
        lines.append(f"配图建议：{page['visual']}")
    overlays = page.get("text_overlay") or []
    if overlays:
        lines.append("画面必须准确呈现的文字：" + "；".join(str(item) for item in overlays))
    if page.get("image_prompt"):
        lines.append("补充视觉要求：" + str(page["image_prompt"]))
    return "\n".join(lines)


def full_outline(plan: dict) -> str:
    blocks = []
    labels = {"cover": "封面", "content": "内容", "summary": "总结"}
    for page in plan["pages"]:
        blocks.append(f"[{labels.get(page.get('type'), '内容')}]\n{page_content(page)}")
    return "\n\n<page>\n\n".join(blocks)


def build_prompt(plan: dict, page: dict, style_count: int, product_count: int) -> str:
    template = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    reference_mapping = "\n".join(
        f"- 风格/构图参考图 @参考图{i}" for i in range(1, style_count + 1)
    ) or "- 无"
    product_mapping = "\n".join(
        f"- 产品植入图 @产品图{i}" for i in range(1, product_count + 1)
    ) or "- 无"
    prompt = template.format(
        page_content=page_content(page),
        page_type=page.get("type", "content"),
        reference_mapping=reference_mapping,
        product_mapping=product_mapping,
        user_topic=(plan.get("brief") or {}).get("topic", "未提供"),
        full_outline=full_outline(plan),
    )
    if product_count:
        prompt = f"{prompt.rstrip()}\n\n{PRODUCT_INSTRUCTION}"
    return prompt


def read_paths(values: list[str], label: str) -> list[tuple[str, bytes]]:
    items: list[tuple[str, bytes]] = []
    for index, raw in enumerate(values or [], 1):
        path = Path(raw).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"{label}{index} 不存在：{path}")
        items.append((f"@{label}{index}", compress_reference(path.read_bytes(), 500 if label == "产品图" else 220)))
    return items


def find_generated(output: Path, index: int, kind: str) -> Path | None:
    matches = sorted(output.glob(f"{index:02d}-{kind}.*"))
    return matches[0] if matches else None


def google_parts(prompt: str, references: list[tuple[str, bytes]]) -> list[dict]:
    parts: list[dict] = []
    if references:
        for _, data in references:
            parts.append({"inlineData": {"mimeType": mime_type(data), "data": base64.b64encode(data).decode("ascii")}})
        mapping = "\n".join(f"- 第 {index} 张输入图片对应 {label}" for index, (label, _) in enumerate(references, 1))
        prompt = f"""你将看到若干张参考图，请严格理解它们与提示词中图片标签的对应关系。

参考图映射：
{mapping}

生成要求：
1. @封面参考图用于锁定整套图文的配色、字体气质、装饰元素、信息层级和版式节奏，后续页必须明显属于同一套视觉系统。
2. @参考图N 只承担提示词指定的风格、构图、人物或场景角色。
3. @产品图N 必须真实植入，不得替换成相似产品或重新设计包装。
4. 最终图片须自然、完整、可直接用于社交媒体发布。

用户提示词：
{prompt}"""
    parts.append({"text": prompt})
    return parts


def generate_google(prompt: str, config: dict, api_key: str, references: list[tuple[str, bytes]]) -> bytes:
    model = urllib.parse.quote(config["model"], safe="-._")
    url = f"{config['base_url'].rstrip('/')}/models/{model}:generateContent?key={urllib.parse.quote(api_key)}"
    image_config = {"aspectRatio": config.get("aspect_ratio", "3:4")}
    if config.get("image_size"):
        image_config["imageSize"] = config["image_size"]
    payload = {
        "contents": [{"role": "user", "parts": google_parts(prompt, references)}],
        "generationConfig": {
            "temperature": config.get("temperature", 1.0),
            "topP": 0.95,
            "maxOutputTokens": 32768,
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": image_config,
        },
    }
    last_error: Exception | None = None
    for _ in range(2):
        try:
            result = request_json(url, payload, {})
            for candidate in result.get("candidates") or []:
                for part in (candidate.get("content") or {}).get("parts") or []:
                    inline = part.get("inlineData") or part.get("inline_data") or {}
                    if inline.get("data"):
                        return base64.b64decode(inline["data"])
            last_error = RuntimeError("Gemini 没有返回图片；请确认模型支持图片输出")
        except Exception as exc:
            last_error = exc
    raise last_error or RuntimeError("Gemini 图片生成失败")


def generate_openai(prompt: str, config: dict, api_key: str) -> bytes:
    url = config["base_url"].rstrip("/") + "/images/generations"
    payload = {
        "model": config["model"], "prompt": prompt, "n": 1,
        "size": config.get("size", "1024x1536"), "quality": config.get("quality", "high"),
        "response_format": "b64_json",
    }
    result = request_json(url, payload, {"Authorization": f"Bearer {api_key}"})
    items = result.get("data") or []
    if items and items[0].get("b64_json"):
        return base64.b64decode(items[0]["b64_json"])
    if items and items[0].get("url"):
        return download(items[0]["url"])
    raise RuntimeError("图片服务没有返回可识别的图片数据")


def main() -> int:
    parser = argparse.ArgumentParser(description="按高保真图文管线生成分页图片")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pages", help="只生成指定页，例如 2,5")
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    errors = validate(plan)
    if errors:
        print("计划验证失败：\n- " + "\n- ".join(errors))
        return 2
    config = load_config()
    provider = config.get("provider")
    if not config or provider == "agent_tool":
        print("当前未配置外部图片 API，请运行 python3 scripts/setup.py")
        return 3
    api_key = load_secret(config.get("credential_name", provider))
    if not api_key:
        print("没有找到 API Key，请重新运行 python3 scripts/setup.py")
        return 2

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    selected = plan["pages"]
    if args.pages:
        wanted = {int(value) for value in args.pages.split(",") if value.strip()}
        selected = [page for page in selected if int(page["index"]) in wanted]
        if wanted - {int(page["index"]) for page in selected}:
            print("指定页不存在")
            return 2

    brief = plan.get("brief") or {}
    shared_style = read_paths(brief.get("reference_images") or [], "参考图")
    shared_products = read_paths(brief.get("product_images") or [], "产品图")
    failures = []
    for position, page in enumerate(selected, 1):
        number, kind = int(page["index"]), page["type"]
        print(f"[{position}/{len(selected)}] 正在生成第 {number} 页 {kind}…")
        try:
            page_style = shared_style + read_paths(page.get("reference_images") or [], "参考图")
            page_products = shared_products + read_paths(page.get("product_images") or [], "产品图")
            references = [*page_style, *page_products]
            if number != 1:
                cover = find_generated(output, 1, "cover")
                if cover:
                    references.append(("@封面参考图", compress_reference(cover.read_bytes(), 220)))
                elif provider == "google":
                    raise RuntimeError("后续页面生成前必须先生成封面")
            prompt = build_prompt(plan, page, len(page_style), len(page_products))
            if provider == "google":
                data = generate_google(prompt, config, api_key, references)
            elif provider in {"openai", "openai_compatible"}:
                if references:
                    print("提示：当前 OpenAI images 适配器不传参考图；高保真模式建议使用 Gemini。")
                data = generate_openai(prompt, config, api_key)
            else:
                raise RuntimeError(f"不支持的 provider：{provider}")
            for old in output.glob(f"{number:02d}-{kind}.*"):
                old.unlink()
            path = output / f"{number:02d}-{kind}{extension(data)}"
            path.write_bytes(data)
            print(f"✓ {path}")
        except Exception as exc:
            failures.append({"index": number, "error": str(exc)})
            print(f"✗ 第 {number} 页失败：{exc}")
    (output / "generation-result.json").write_text(
        json.dumps({"success": not failures, "pipeline": "high_fidelity_v2", "failures": failures, "model": config.get("model")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
