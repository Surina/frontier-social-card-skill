#!/usr/bin/env python3
"""Beginner-friendly image provider setup wizard."""

from __future__ import annotations

import argparse
import sys

from config import config_path, delete_secret, load_config, load_secret, read_secret, save_config, save_secret


PROVIDERS = {
    "1": {"provider": "agent_tool", "label": "使用当前 Agent 的图片能力（推荐）", "model": ""},
    "2": {"provider": "openai", "label": "OpenAI", "model": "gpt-image-1"},
    "3": {"provider": "google", "label": "Google Gemini（支持封面风格统一）", "model": "gemini-3-pro-image"},
    "4": {"provider": "openai_compatible", "label": "其他 OpenAI 兼容服务", "model": ""},
}


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}：").strip()
    return value or default


def status() -> int:
    config = load_config()
    if not config:
        print("尚未配置。请运行：python3 scripts/setup.py")
        return 1
    provider = config.get("provider", "agent_tool")
    print(f"图片生成方式：{provider}")
    if config.get("model"):
        print(f"模型：{config['model']}")
    if config.get("quality_profile"):
        print(f"质量模式：{config['quality_profile']}")
    text_provider = config.get("text_provider") or provider
    text_model = config.get("text_model") or ("gemini-3.5-flash" if text_provider == "google" else "未单独配置")
    print(f"大纲模型：{text_provider} / {text_model}")
    if provider != "agent_tool":
        print("API Key：已配置" if load_secret(config.get("credential_name", "default")) else "API Key：未配置")
    print(f"配置位置：{config_path()}")
    return 0


def configure() -> int:
    print("\n欢迎使用 frontier-social-card-skill Skill\n")
    print("请选择图片生成方式：\n")
    for key, item in PROVIDERS.items():
        print(f"{key}. {item['label']}")
    choice = ask("请选择", "1")
    if choice not in PROVIDERS:
        print("选择无效，请重新运行配置。")
        return 2

    selected = dict(PROVIDERS[choice])
    selected.pop("label")
    config = {
        "version": 1,
        **selected,
        "base_url": "",
        "aspect_ratio": "3:4",
        "size": "1024x1536",
        "quality": "high",
        "quality_profile": "standard",
        "temperature": 1.0,
        "text_provider": selected["provider"],
        "text_model": "",
        "text_base_url": "",
        "text_temperature": 1.0,
        "text_max_output_tokens": 8000,
        "text_credential_name": selected["provider"],
        "credential_name": selected["provider"],
    }
    if selected["provider"] == "agent_tool":
        save_config(config)
        print("\n✓ 配置完成，无需 API Key。")
        print("现在可以让 Agent 帮你制作一套完整图文。")
        return 0

    if selected["provider"] == "openai":
        config["base_url"] = "https://api.openai.com/v1"
        config["model"] = ask("模型名称", config["model"])
        config["text_base_url"] = config["base_url"]
        config["text_model"] = "gpt-4.1"
    elif selected["provider"] == "google":
        config["base_url"] = "https://generativelanguage.googleapis.com/v1beta"
        print("\n请选择质量模式：\n")
        print("1. 质量优先（推荐，效果更接近专业图文工作流）")
        print("2. 均衡模式（速度更快、成本更低）")
        quality_choice = ask("请选择", "1")
        if quality_choice == "2":
            config["quality_profile"] = "balanced"
            config["model"] = "gemini-3.1-flash-image"
            config["image_size"] = "2K"
        else:
            config["quality_profile"] = "quality"
            config["model"] = "gemini-3-pro-image"
            config["image_size"] = "2K"
        config["model"] = ask("模型名称", config["model"])
        config["text_base_url"] = "https://generativelanguage.googleapis.com/v1beta"
        config["text_model"] = ask("大纲文本模型", "gemini-3.5-flash")
    else:
        config["base_url"] = ask("服务地址，例如 https://example.com/v1")
        config["model"] = ask("模型名称")
        if not config["base_url"] or not config["model"]:
            print("服务地址和模型名称不能为空。")
            return 2
        config["text_base_url"] = config["base_url"]
        config["text_model"] = ask("大纲文本模型")

    key = read_secret("请输入 API Key（输入内容不会显示）：")
    if not key:
        print("没有输入 API Key，配置未保存。")
        return 2
    storage = save_secret(config["credential_name"], key)
    save_config(config)
    print("\n✓ 配置已保存。")
    if storage == "private_file":
        print("提示：系统密钥库不可用，密钥已保存到仅当前用户可读的本地文件。")
    print("运行 python3 scripts/setup.py --status 可随时查看配置。")
    return 0


def set_quality(profile: str) -> int:
    config = load_config()
    if config.get("provider") != "google":
        print("只有 Google Gemini 配置支持质量模式切换。")
        return 2
    if profile == "quality":
        config.update({"quality_profile": "quality", "model": "gemini-3-pro-image", "image_size": "2K"})
    else:
        config.update({"quality_profile": "balanced", "model": "gemini-3.1-flash-image", "image_size": "2K"})
    save_config(config)
    print(f"✓ 已切换为 {profile}：{config['model']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="配置图文 Skill 的图片生成方式")
    parser.add_argument("--status", action="store_true", help="查看当前配置")
    parser.add_argument("--reset", action="store_true", help="删除当前配置中的密钥")
    parser.add_argument("--set-quality", choices=["quality", "balanced"], help="切换 Gemini 质量模式，不需要重新输入密钥")
    args = parser.parse_args()
    if args.status:
        return status()
    if args.reset:
        current = load_config()
        delete_secret(current.get("credential_name", "default"))
        save_config({})
        print("✓ 配置已重置。")
        return 0
    if args.set_quality:
        return set_quality(args.set_quality)
    return configure()


if __name__ == "__main__":
    sys.exit(main())
