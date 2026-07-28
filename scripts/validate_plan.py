#!/usr/bin/env python3
"""Validate a standalone social image-post plan."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        return ["pages 必须是非空数组"]
    if pages[0].get("type") != "cover":
        errors.append("第一页必须是 cover")
    expected = list(range(1, len(pages) + 1))
    actual = [page.get("index") for page in pages]
    if actual != expected:
        errors.append(f"页码必须从 1 连续排列，当前为 {actual}")
    for page in pages:
        if page.get("type") not in {"cover", "content", "summary"}:
            errors.append(f"第 {page.get('index', '?')} 页 type 无效")
        raw_content = page.get("content") or page.get("raw_content")
        if raw_content:
            if not str(raw_content).strip():
                errors.append(f"第 {page.get('index', '?')} 页 content 为空")
            continue
        required = {"headline", "body", "visual", "text_overlay", "image_prompt"}
        missing = sorted(key for key in required if key not in page)
        if missing:
            errors.append(f"第 {page.get('index', '?')} 页缺少字段：{', '.join(missing)}")
        if not str(page.get("image_prompt", "")).strip():
            errors.append(f"第 {page.get('index', '?')} 页 image_prompt 为空")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：python3 scripts/validate_plan.py <plan.json>")
        return 2
    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"无法读取计划：{exc}")
        return 2
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"✗ {error}")
        return 1
    print(f"✓ 计划有效，共 {len(data['pages'])} 页。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
