# Frontier Social Card Skill

> 把主题、文章、草稿和产品素材，变成一套可以继续修改和发布的小红书图文。

`frontier-social-card-skill` 是一个面向 Codex / Claude 等本地 AI Agent 的独立 Skill。它可以生成一整套风格一致、符合用户提供主题或者内容的爆款图文：

**内容拆解 → 分页大纲 → 用户确认 → 发布文案 → 分页配图 → 完整交付**

默认面向小红书（Xiaohongshu / RedNote / RedBook），支持中文内容、3:4 竖版卡片、产品参考图和视觉风格参考图。

[30 秒开始](#30-秒开始) · [它能做什么](#它能做什么) · [安装与配置](#安装与配置) · [English](#english)

## 30 秒开始

安装完成后，在 Codex 中直接说：

```text
使用 $frontier-social-card-skill，把这篇文章制作成一套 7 页小红书图文。
```

也可以从一个简单主题开始：

```text
使用 $frontier-social-card-skill，做一套“小团队如何用 AI 做内容营销”的
小红书图文，目标读者是独立创业者，风格专业但不要太像课程广告。
```

如果有参考图或产品图，可以一起提供：

```text
使用 $frontier-social-card-skill，为这个产品制作一套面向澳洲华人的
RedNote 种草图文。第一张图只参考视觉风格，第二、三张是产品图，
请保留包装、颜色和品牌识别。
```

Skill 会先给出完整的分页大纲。你可以逐页修改；确认后，它才会生成发布文案和图片。这样可以在花时间出图前先把内容结构定好。

## 它是什么

普通生图提示词解决的是“生成一张图”。`frontier-social-card-skill` 解决的是“完成一整套图文”：

- 从主题、草稿或长文中提取适合社交媒体阅读的内容主线
- 把内容拆成有开头、展开和收束的 6–8 页图文
- 为每一页规划标题、正文重点、画面和文字关系
- 先生成封面，再用封面约束后续页面的视觉一致性
- 同时生成主标题、备选标题、小红书正文和标签
- 交付按页编号的图片、详细大纲和结构化 JSON 文件

它是一个 Agent 工作流，不是独立 App，也不会自动登录或发布到小红书。

## 它能做什么

### 支持的输入

| 输入 | Skill 如何使用 |
| --- | --- |
| 一个主题或想法 | 补全为可执行的内容结构和分页大纲 |
| 已有草稿或长文 | 提炼重点并改写成适合移动端阅读的组图 |
| 普通参考图 | 参考构图、配色、氛围、材质和版式语言 |
| 产品图片 | 作为需要保留外观和品牌识别的核心素材 |
| 明确要求 | 接收目标受众、内容目的、页数、语气和视觉方向 |

普通参考图和产品图的处理方式不同：普通参考图用于借鉴风格；产品图会被视为身份敏感素材，尽量保留包装、颜色、形状和可识别细节。

### 默认设置

如果没有特别说明，Skill 会采用：

- 平台：小红书 / RedNote
- 语言：中文
- 页数：6–8 页
- 画布：3:4 竖版
- 结构：封面 + 内容页 + 可选总结/行动页
- 阅读场景：手机信息流

这些默认值都可以在请求中覆盖。

### 最终输出

一次完整任务通常会得到：

```text
任务输出目录/
├── outline.json       # 用户确认过的详细分页大纲
├── content.json       # 主标题、备选标题、发布正文和标签
├── 01-*.png           # 封面
├── 02-*.png           # 内容页
├── 03-*.png
└── ...
```

Agent 会在对话中按顺序展示每一页，而不是只给封面或一个文件夹路径。

## 适合 / 不适合

**适合：**

- 长文章、博客或访谈内容转小红书图文
- 知识分享、教程拆页、方法论和清单
- 产品介绍、种草笔记和品牌内容
- 有产品图、截图或视觉参考图的整套组图
- 需要同时完成图片、标题、正文和标签的内容任务
- 希望先确认内容，再投入图片生成成本的工作流

**不适合：**

- 自动登录、定时发布或运营小红书账号
- 单纯修图、抠图或替换图片局部
- 长视频剪辑、Live Photo 或动画制作
- 横向演示文稿和 PPT
- 要求像素级复刻他人作品、商标或水印
- 只需要一段纯文字、不需要分页视觉内容的任务

## 使用流程

Skill 默认分成两个阶段，避免“内容还没定，图片已经出完”。

### 阶段一：生成并确认大纲

1. 读取主题、原文和图片素材
2. 生成逐页详细大纲
3. 展示每一页的内容和画面建议
4. 等待你确认，或只修改你点名的页面

你可以这样反馈：

```text
第 3 页太抽象，换成一个具体案例；第 5 页保留。封面标题再短一点。
```

也可以直接确认：

```text
确认，按这个大纲开始生成。
```

### 阶段二：生成文案和图片

确认后，Skill 会：

1. 生成主标题、备选标题、发布正文和标签
2. 先生成封面
3. 将封面作为后续页面的视觉参考
4. 按页生成剩余图片
5. 检查缺页、乱码、文字可读性和明显的风格漂移
6. 交付所有图片及 JSON 文件

除非你明确说“跳过确认，直接生成”，否则 Skill 不会把两个阶段合并。

## 更多可直接复制的请求

### 文章转组图

```text
使用 $frontier-social-card-skill，把附件文章改成 8 页小红书图文。
保留原文观点，不新增未经证实的数据。语气简洁、可信，不要营销腔。
```

### 产品种草

```text
使用 $frontier-social-card-skill，为这款产品做 6 页种草图文。
受众是第一次接触这个品类的人。产品图片必须保留包装颜色和 Logo，
不要虚构价格、认证或用户评价。
```

### 知识教程

```text
使用 $frontier-social-card-skill，把“如何做一份竞品分析”拆成 7 页教程卡片。
每页只讲一个重点，封面要有明确收益，但不要标题党。
```

### 只先做策划

```text
使用 $frontier-social-card-skill，先为这个主题生成分页大纲和每页画面建议，
暂时不要生成图片。
```

## 安装与配置

### 环境要求

- Codex 或其他能够读取 Skill、操作本地文件并运行 Python 的 AI Agent
- Python 3.10 或更高版本
- 如果使用外部图片 API，需要安装 `requirements.txt` 中的依赖

普通网页聊天机器人没有本地文件和图片生成管线，无法完整运行这个 Skill。

### 1. 安装 Skill

使用 HTTPS：

```bash
git clone https://github.com/Surina/frontier-social-card.git \
  ~/.codex/skills/frontier-social-card-skill
```

或使用 SSH：

```bash
git clone git@github.com:Surina/frontier-social-card.git \
  ~/.codex/skills/frontier-social-card-skill
```

重新打开 Codex 对话后，即可通过 `$frontier-social-card-skill` 调用。

### 2. 安装外部 API 依赖

如果只使用 Agent 自带的图片生成能力，可以跳过这一步。使用 Google Gemini、OpenAI 或兼容 API 时运行：

```bash
python3 -m pip install -r \
  ~/.codex/skills/frontier-social-card-skill/requirements.txt
```

### 3. 运行配置向导

```bash
python3 ~/.codex/skills/frontier-social-card-skill/scripts/setup.py
```

向导支持：

1. 当前 Agent 自带的图片生成能力（无需 API Key）
2. OpenAI
3. Google Gemini
4. 其他 OpenAI 兼容服务

查看当前配置：

```bash
python3 ~/.codex/skills/frontier-social-card-skill/scripts/setup.py --status
```

Gemini 用户可以切换质量模式：

```bash
python3 ~/.codex/skills/frontier-social-card-skill/scripts/setup.py \
  --set-quality quality
```

配置完成后，直接回到 Agent 对话中描述任务即可；日常使用不需要手动运行生成脚本。

## 图片生成方式

Skill 优先使用当前 Agent 已经具备的图片生成工具。如果 Agent 没有图片能力，也可以配置自己的服务：

| 方式 | 是否需要 API Key | 适合场景 |
| --- | --- | --- |
| Agent 自带图片工具 | 通常不需要 | 最简单，安装后直接使用 |
| Google Gemini | 需要 | 需要参考图和多模态图片生成 |
| OpenAI | 需要 | 已有 OpenAI 图片 API 配置 |
| OpenAI 兼容服务 | 视服务而定 | 使用自建网关或兼容供应商 |

如果当前环境无法生成图片，Skill 仍可完成大纲、发布文案和逐页图片提示词，不会阻塞前期内容策划。

## 内容与视觉原则

- 内容先于装饰：每一页只承担一个清晰的信息任务
- 封面先行：用封面统一后续页面的视觉语言
- 手机可读：控制文字密度，避免小字号和大段正文
- 尊重素材：不复刻水印、账号 ID 或平台 Logo
- 产品保真：尽量保留产品包装、颜色、形状和品牌识别
- 事实克制：不虚构数据、认证、功效、价格、背书或用户评价
- 人工确认：生成内容不等于获得发布授权

如果图片模型无法稳定生成中文，Skill 应优先生成干净的背景或插画，并提供准确的文字叠加说明，而不是接受乱码结果。

## 隐私与密钥

- 不在聊天中索取、显示或记录 API Key
- 优先把密钥存入系统密钥库
- 系统密钥库不可用时，才保存到仅当前用户可读的本地配置文件
- 不把密钥写入图片、文案、JSON 或仓库
- 不会自动发布或向外部账号发送内容

## 项目结构

```text
frontier-social-card-skill/
├── SKILL.md                  # Agent 执行工作流
├── README.md                 # 面向使用者的说明
├── agents/openai.yaml        # Codex 中的显示信息与默认提示词
├── assets/
│   ├── outline_prompt.txt    # 大纲生成提示体系
│   ├── content_prompt.txt    # 发布文案提示体系
│   ├── image_prompt.txt      # 分页图片提示体系
│   └── config.example.json   # 配置示例
├── references/               # 文案、结构、视觉和输出规范
├── scripts/
│   ├── setup.py              # 本地配置向导
│   ├── generate_outline.py   # 生成详细分页大纲
│   ├── generate_content.py   # 生成发布文案
│   ├── generate.py           # 生成分页图片
│   └── validate_plan.py      # 校验结构化计划
└── requirements.txt
```

`README.md` 帮助人理解和安装；`SKILL.md` 是 Agent 实际执行时遵循的指令。两者用途不同。

## FAQ

### 一定要提供一篇完整文章吗？

不需要。一个主题、一段草稿、几张产品图，或它们的组合都可以。提供的受众、目的和素材越明确，结果越可控。

### 可以指定页数和风格吗？

可以。直接在请求中说明页数、语气、视觉方向、目标受众和内容目的。未指定时使用 6–8 页、中文和 3:4 竖版。

### 为什么要先确认大纲？

组图的返工成本主要来自结构，而不是单张图片。先确认逐页内容，可以减少生成后才发现漏重点、顺序不对或标题方向错误的情况。

### 可以跳过确认吗？

可以。明确说“跳过大纲确认，直接生成”即可。对于长文章、产品内容和页数较多的任务，仍建议保留确认步骤。

### 产品图会被改掉吗？

Skill 会把产品图作为需要保留身份的素材，但最终保真度仍取决于所使用的图片模型。对于包装文字、Logo 和精细结构，应在交付时人工复核。

### 图片生成失败怎么办？

成功页面会被保留，只重试失败或明显有问题的页面。若当前环境没有可用图片模型，仍会交付大纲、文案和可复用的逐页提示词。

### 如何更新？

```bash
cd ~/.codex/skills/frontier-social-card-skill
git pull
```

## English

`frontier-social-card-skill` is a standalone Skill for Codex and other local AI agents. It turns a topic, draft, article, visual reference, or product image into a complete Xiaohongshu / RedNote carousel:

**content analysis → page outline → user approval → post copy → generated pages → final delivery**

It defaults to Chinese, 6–8 mobile-friendly pages, and a vertical 3:4 canvas. It can use the current agent's built-in image tool or a user-configured Google Gemini, OpenAI, or OpenAI-compatible image API.

### Quick start

```text
Use $frontier-social-card-skill to turn this article into a seven-page
Xiaohongshu / RedNote carousel. Keep the claims grounded in the source.
```

The Skill first presents a detailed page-by-page outline. After approval, it creates titles, post copy, tags, and numbered images. Provide an audience, objective, page count, tone, visual references, or product images whenever needed.

### Install

```bash
git clone https://github.com/Surina/frontier-social-card.git \
  ~/.codex/skills/frontier-social-card-skill

python3 ~/.codex/skills/frontier-social-card-skill/scripts/setup.py
```

Python 3.10 or later is required. If you use an external API, install the dependencies:

```bash
python3 -m pip install -r \
  ~/.codex/skills/frontier-social-card-skill/requirements.txt
```

API keys are collected locally by the setup wizard and are never requested in chat, committed to the repository, or embedded in generated artifacts. The Skill does not log in to social platforms or publish content automatically.

## License

[MIT](LICENSE)

---

Keywords: 小红书, 小红书图文, Xiaohongshu, RedNote, RedBook, social cards, carousel posts, AI image generation, Codex Skill.
