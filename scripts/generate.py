#!/usr/bin/env python3
"""Standalone high-fidelity social-card image pipeline."""

from __future__ import annotations

import argparse
import base64
import io
import json
import ssl
import sys
import time
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
    request = urllib.request.Request(url, headers={"User-Agent": "frontier-social-card-skill/2.0"})
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


def compress_reference(data: bytes, max_kb: int = 80) -> bytes:
    if len(data) <= max_kb * 1024:
        return data
    try:
        from PIL import Image  # type: ignore

        image = Image.open(io.BytesIO(data))
        image.load()
        if image.mode in {"RGBA", "LA", "P"}:
            if image.mode == "P":
                image = image.convert("RGBA")
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode in {"RGBA", "LA"} else None)
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")
        image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
        compressed = data
        for quality in range(85, 19, -5):
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True)
            compressed = output.getvalue()
            if len(compressed) <= max_kb * 1024:
                return compressed
        width, height = image.size
        while len(compressed) > max_kb * 1024 and max(width, height) > 512:
            width, height = int(width * 0.9), int(height * 0.9)
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            resized.save(output, format="JPEG", quality=20, optimize=True)
            compressed = output.getvalue()
        return compressed
    except Exception:
        return data


def compress_product_image(data: bytes, max_kb: int = 256) -> bytes:
    if len(data) <= max_kb * 1024:
        return data
    try:
        from PIL import Image  # type: ignore

        image = Image.open(io.BytesIO(data))
        image.load()
        image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        has_alpha = image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info)
        output = io.BytesIO()
        if has_alpha:
            image.convert("RGBA").save(output, format="PNG", optimize=True)
            return output.getvalue()
        image = image.convert("RGB")
        compressed = data
        for quality in range(95, 59, -5):
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True)
            compressed = output.getvalue()
            if len(compressed) <= max_kb * 1024:
                break
        return compressed
    except Exception:
        return data


def page_content(page: dict) -> str:
    raw = page.get("content") or page.get("raw_content")
    if raw:
        return str(raw).strip()
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
    if str(plan.get("source_outline") or "").strip():
        return str(plan["source_outline"]).strip()
    blocks = []
    for page in plan["pages"]:
        blocks.append(page_content(page))
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
        data = path.read_bytes()
        data = compress_product_image(data) if label == "产品图" else compress_reference(data, 80)
        items.append((f"@{label}{index}", data))
    return items


def find_generated(output: Path, index: int, kind: str) -> Path | None:
    matches = sorted(output.glob(f"{index:02d}-{kind}.*"))
    return matches[0] if matches else None


def google_parts(prompt: str, references: list[tuple[str, bytes]], types_module=None) -> list:
    parts: list = []
    if references:
        for label, data in references:
            compressed = compress_product_image(data) if label.startswith("@产品图") else compress_reference(data, 80)
            if types_module is None:
                parts.append({"inlineData": {"mimeType": mime_type(compressed), "data": base64.b64encode(compressed).decode("ascii")}})
            else:
                parts.append(types_module.Part(
                    inline_data=types_module.Blob(mime_type=mime_type(compressed), data=compressed)
                ))
        mapping = "\n".join(f"- 第 {index} 张输入图片对应 {label}" for index, (label, _) in enumerate(references, 1))
        prompt = f"""你将看到若干张参考图，请严格理解它们与提示词中图片标签的对应关系。

参考图映射：
{mapping}

生成要求：
1. 如果提示词要求“把产品 @产品图1 进行植入”或类似表达，必须把对应图片中的主体/产品真实地出现在生成结果中，而不只是参考风格。
2. 如果提示词同时引用多个图片标签，要分别理解每张参考图承担的角色，例如人物、产品、场景、构图或风格。
3. 除非提示词明确要求替换主体，否则要优先保留被引用参考图中的核心主体特征。
4. 最终图片仍需保持自然、真实、可用，不能只做抽象致敬或弱化产品存在感。

用户提示词：
{prompt}"""
    parts.append({"text": prompt} if types_module is None else types_module.Part(text=prompt))
    return parts


def read_google_response(response) -> tuple[bytes | None, list[str]]:
    """Extract image bytes and useful diagnostics from a Gemini response or chunk."""
    diagnostics: list[str] = []
    prompt_feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(prompt_feedback, "block_reason", None) if prompt_feedback else None
    if block_reason:
        diagnostics.append(f"prompt block reason: {block_reason}")

    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            data = getattr(inline, "data", None) if inline is not None else None
            if data:
                if isinstance(data, str):
                    try:
                        data = base64.b64decode(data)
                    except Exception:
                        diagnostics.append("image data was not valid base64")
                        continue
                return bytes(data), diagnostics
            response_text = str(getattr(part, "text", "") or "").strip()
            if response_text:
                diagnostics.append(f"model response: {response_text[:300]}")
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason:
            diagnostics.append(f"finish reason: {finish_reason}")
    return None, diagnostics


def generate_google(prompt: str, config: dict, api_key: str, references: list[tuple[str, bytes]]) -> bytes:
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except ImportError as exc:
        raise RuntimeError("缺少 google-genai，请运行：python3 -m pip install google-genai") from exc

    http_options: dict = {"api_version": "v1beta", "timeout": int(config.get("request_timeout_ms") or 180000)}
    base_url = str(config.get("base_url") or "").rstrip("/")
    if base_url and base_url != "https://generativelanguage.googleapis.com/v1beta":
        http_options["base_url"] = base_url
    client = genai.Client(
        api_key=api_key,
        vertexai=False,
        http_options=types.HttpOptions(**http_options),
    )
    def make_contents(request_prompt: str) -> list:
        return [
            types.Content(
                role="user",
                parts=google_parts(request_prompt, references, types),
            )
        ]

    contents = make_contents(prompt)
    generation_config = types.GenerateContentConfig(
        temperature=config.get("temperature", 1.0),
        top_p=0.95,
        # Image responses can consume far more output tokens than text. A 1024
        # fallback intermittently ends valid image requests with MAX_TOKENS.
        max_output_tokens=int(config.get("max_output_tokens") or 32768),
        response_modalities=["TEXT", "IMAGE"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        image_config=types.ImageConfig(aspect_ratio=config.get("aspect_ratio", "3:4")),
    )

    diagnostics: list[str] = []
    for attempt in range(2):
        try:
            for chunk in client.models.generate_content_stream(
                model=config["model"],
                contents=contents,
                config=generation_config,
            ):
                image_data, chunk_diagnostics = read_google_response(chunk)
                diagnostics.extend(chunk_diagnostics)
                if image_data:
                    return image_data
            break
        except Exception as exc:
            text = str(exc).lower()
            if attempt == 0 and any(token in text for token in ("500", "internal", "503", "unavailable")):
                time.sleep(1.5)
                continue
            raise

    # A normal STOP can still contain only text. Always try the regular endpoint
    # before treating a text-only streaming response as a failed image request.
    try:
        response = client.models.generate_content(
            model=config["model"],
            contents=contents,
            config=generation_config,
        )
        image_data, response_diagnostics = read_google_response(response)
        diagnostics.extend(response_diagnostics)
        if image_data:
            return image_data
    except Exception as exc:
        diagnostics.append(f"non-stream request failed: {exc}")

    # Gemini may occasionally answer an image request with explanatory text.
    # Make one explicit corrective request while preserving the original prompt
    # and all reference-image inputs.
    corrective_prompt = (
        f"{prompt.rstrip()}\n\n"
        "【输出纠偏】上一轮没有返回图片。请不要解释、分析或回复文字，"
        "必须直接生成并返回一张符合以上要求的完整图片。"
    )
    try:
        response = client.models.generate_content(
            model=config["model"],
            contents=make_contents(corrective_prompt),
            config=generation_config,
        )
        image_data, response_diagnostics = read_google_response(response)
        diagnostics.extend(response_diagnostics)
        if image_data:
            return image_data
    except Exception as exc:
        diagnostics.append(f"corrective request failed: {exc}")

    detail = "；".join(dict.fromkeys(diagnostics))[:600]
    raise RuntimeError(f"Gemini 没有返回图片：{detail or '没有候选内容或图片数据'}")


def plan_from_outline(data: dict) -> dict:
    pages = data.get("pages") or []
    if not pages:
        raise ValueError("outline.json 中没有 pages")
    return {
        "version": 1,
        "brief": {
            "topic": str(data.get("topic") or ""),
            "reference_images": list(data.get("reference_images") or []),
            "product_images": list(data.get("product_images") or []),
        },
        "source_outline": str(data.get("outline") or ""),
        "pages": [
            {
                "index": int(page["index"]),
                "type": page.get("type") or "content",
                "content": str(page.get("content") or "").strip(),
            }
            for page in pages
        ],
    }


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
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--outline", help="generate_outline.py 生成并经用户确认的 outline.json")
    source.add_argument("--plan", help="旧版结构化 plan.json（兼容模式）")
    parser.add_argument("--output", required=True)
    parser.add_argument("--pages", help="只生成指定页，例如 2,5")
    args = parser.parse_args()
    source_path = args.outline or args.plan
    source_data = json.loads(Path(source_path).read_text(encoding="utf-8"))
    plan = plan_from_outline(source_data) if args.outline else source_data
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
    result_path = output / "generation-result.json"
    previous_result: dict = {}
    if result_path.exists():
        try:
            previous_result = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception:
            previous_result = {}
    failure_map = {
        int(item["index"]): str(item.get("error") or "")
        for item in previous_result.get("failures", [])
        if str(item.get("index", "")).isdigit()
    }
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
                    references.append(("@封面参考图", compress_reference(cover.read_bytes(), 80)))
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
            failure_map.pop(number, None)
            print(f"✓ {path}")
        except Exception as exc:
            failure_map[number] = str(exc)
            print(f"✗ 第 {number} 页失败：{exc}")
            if number == 1:
                print("封面生成失败，已停止后续页面；修复后可仅重试封面。")
                break

    generated = []
    missing = []
    for page in plan["pages"]:
        number, kind = int(page["index"]), page["type"]
        path = find_generated(output, number, kind)
        if path:
            generated.append({"index": number, "path": str(path.resolve())})
        else:
            missing.append(number)
    failures = [
        {"index": index, "error": error}
        for index, error in sorted(failure_map.items())
    ]
    success = not failures and not missing
    status = "completed" if success else ("partial" if generated else "failed")
    result_path.write_text(
        json.dumps(
            {
                "success": success,
                "status": status,
                "pipeline": "high_fidelity_v2",
                "generated": generated,
                "missing": missing,
                "failures": failures,
                "model": config.get("model"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
