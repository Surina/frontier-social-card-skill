# Frontier Social Card

> 为小红书（Xiaohongshu / RedNote / RedBook）创作完整图文内容的独立 AI Agent Skill。  
> An independent AI Agent skill for creating complete Xiaohongshu (RedNote / RedBook) carousel posts.

[中文](#中文) · [English](#english)

## 中文

`frontier-social-card` 可以把一个主题、草稿、长文、参考图片或产品图片，转化为一套适合小红书发布的完整图文内容。

安装后，可以使用当前 Agent 自带的图片能力，或配置自己的 Google Gemini、OpenAI 或 OpenAI 兼容图片 API。

### 主要能力

- 以小红书（RedNote、RedBook、Xiaohongshu）为主要发布平台
- 从主题、文章或草稿生成详细分页大纲
- 先展示大纲，获得确认后再生成图片
- 生成封面标题、分页文案、发布正文、备选标题和标签
- 支持普通参考图和需要保留外观的产品图
- 先生成封面，再用封面统一后续页面的视觉风格
- 默认生成适合移动端阅读的 3:4 竖版卡片
- 支持 Agent 原生图片工具和用户自己的图片 API
- 生成后按页展示整套图片，并保留结构化 JSON 计划

### 工作流程

```text
主题 / 草稿 / 长文 / 图片
        ↓
生成详细分页大纲
        ↓
用户确认或修改
        ↓
生成发布文案与页面计划
        ↓
逐页生成图片并检查一致性
        ↓
交付完整图文、文案和 JSON
```

大纲确认和图片生成是两个阶段。除非用户明确要求跳过确认，否则 Skill 不会在大纲确认前调用图片模型。

### 安装

需要 Python 3.10 或更高版本。

```bash
git clone git@github.com:Surina/frontier-social-card.git \
  ~/.codex/skills/frontier-social-card
```

也可以使用 HTTPS：

```bash
git clone https://github.com/Surina/frontier-social-card.git \
  ~/.codex/skills/frontier-social-card
```

重新打开 Codex 对话后，即可通过 `$frontier-social-card` 调用。

### 首次配置

运行配置向导：

```bash
python3 ~/.codex/skills/frontier-social-card/scripts/setup.py
```

向导支持：

1. 当前 Agent 自带的图片生成能力（无需 API Key）
2. OpenAI
3. Google Gemini
4. 其他 OpenAI 兼容服务

检查当前配置：

```bash
python3 ~/.codex/skills/frontier-social-card/scripts/setup.py --status
```

Google Gemini 用户还可以切换质量模式：

```bash
python3 ~/.codex/skills/frontier-social-card/scripts/setup.py --set-quality quality
```

API Key 不会写入仓库或生成文件。Skill 优先使用系统密钥库；系统密钥库不可用时，才会保存到仅当前用户可读的本地配置位置。

### 使用示例

```text
使用 $frontier-social-card，把这篇文章制作成一套 7 页小红书图文。
```

```text
使用 $frontier-social-card，为这个产品生成一套面向澳洲华人的
RedNote 种草图文，并保留产品包装和品牌识别。
```

你也可以提供：

- 目标受众和内容目的
- 希望的页数、语气和视觉风格
- 参考文章或已有草稿
- 风格参考图
- 产品图片

未指定时，默认使用中文、小红书平台、6–8 页和 3:4 竖版画布。

### 输出

完整任务通常包括：

- 已确认的详细分页大纲
- 主标题和备选标题
- 小红书发布正文与标签
- 结构化页面计划 JSON
- 按页编号的封面、内容页和总结页图片

### 独立性与隐私

- 不连接 GenieRabbit API、数据库或账号系统
- 不要求安装或运行 GenieRabbit
- 不在聊天中请求、显示或记录 API Key
- 不把密钥写入生成图片、文案或计划文件
- 生成内容不代表已经获得外部发布授权

## English

`frontier-social-card` turns a topic, draft, long-form article, reference image, or product image into a complete visual post designed primarily for Xiaohongshu—also known internationally as RedNote or RedBook.

It runs independently from any product backend. You can use an image-generation tool already available to your Agent or configure your own Google Gemini, OpenAI, or OpenAI-compatible image API.

### Features

- Optimized for Xiaohongshu, RedNote, and RedBook carousel posts
- Generates a detailed page-by-page outline from a topic, article, or draft
- Requires outline approval before image generation
- Creates cover copy, page copy, post captions, alternative titles, and tags
- Supports visual reference images and identity-sensitive product images
- Uses the generated cover as a visual reference for consistent later pages
- Defaults to mobile-friendly vertical 3:4 social cards
- Supports native Agent image tools and user-configured image APIs
- Delivers every generated page together with a structured JSON plan

### Workflow

```text
Topic / draft / article / images
              ↓
Generate a detailed page outline
              ↓
User review and approval
              ↓
Create publication copy and page plan
              ↓
Generate and inspect each image
              ↓
Deliver the complete carousel, copy, and JSON
```

Outline approval and image creation are separate phases. The skill does not call an image model before approval unless the user explicitly asks to skip confirmation.

### Installation

Python 3.10 or later is recommended.

```bash
git clone https://github.com/Surina/frontier-social-card.git \
  ~/.codex/skills/frontier-social-card
```

Start a new Codex conversation, then invoke the skill as `$frontier-social-card`.

### First-time setup

```bash
python3 ~/.codex/skills/frontier-social-card/scripts/setup.py
```

The setup wizard supports:

1. The current Agent's built-in image capability, with no API key required
2. OpenAI
3. Google Gemini
4. Other OpenAI-compatible services

Check the current configuration:

```bash
python3 ~/.codex/skills/frontier-social-card/scripts/setup.py --status
```

API keys are never committed to the repository or included in generated artifacts. The skill prefers the operating system's secure credential store and falls back to a private local credential file only when necessary.

### Example

```text
Use $frontier-social-card to turn this article into a seven-page
Xiaohongshu / RedNote carousel post.
```

You may also provide an audience, objective, page count, tone, visual direction, reference images, and product images.

### Output

A completed task normally includes:

- An approved detailed outline
- A selected title and alternatives
- Xiaohongshu post copy and tags
- A structured JSON page plan
- Numbered cover, content, and summary images

### Independence and privacy

- Does not connect to GenieRabbit APIs, databases, or accounts
- Does not require GenieRabbit to be installed or running
- Never asks for or reveals API keys in chat
- Never embeds credentials in generated images, copy, or plan files
- Content creation does not authorize external publishing

## License

[MIT](LICENSE)

---

Keywords: 小红书, 小红书图文, Xiaohongshu, RedNote, RedBook, social cards, carousel posts, AI image generation, Codex Skill.
