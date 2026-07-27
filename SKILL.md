---
name: frontier-social-card
description: Create complete Xiaohongshu social-media image posts and carousel cards from a topic, draft, article, reference images, or product images, including page planning, cover copy, titles, post body, tags, per-page visual prompts, and generated images. Use for 小红书图文、RedNote、RedBook、Xiaohongshu、社交媒体轮播图、分页知识卡片、种草笔记、产品图文、封面和整套配图创作。
---

# Frontier Social Card

Create a complete image post locally with the current agent's reasoning and image capabilities. Do not call, import, require, or connect to any external product backend.

## Quiet operation

Keep user-facing commentary minimal during outline and image generation. Do not narrate internal reasoning, prompt construction, file handling, API details, or step-by-step progress unless there is an error, a blocking configuration issue, or the user explicitly asks for status. Use at most one short start message before a long run, then deliver the outline or finished images when ready.

## First run

Before the first creation request, run `python3 scripts/setup.py --status`. If it reports that no configuration exists:

1. If the current agent has an image-generation tool, run `printf '1\n' | python3 scripts/setup.py` to select it automatically and tell the user no API key is needed.
2. Otherwise, tell the user to run `python3 scripts/setup.py` locally. The wizard collects provider choices and secrets; never collect an API key in chat.
3. Do not block text planning while image setup is incomplete. Create the plan and image prompts, then give the user the single setup command needed to generate images.

When distributing or installing this skill manually, always show this setup command after copying the folder:

```bash
python3 ~/.codex/skills/frontier-social-card/scripts/setup.py
```

## Choose the image path

1. Prefer an image-generation tool already available to the current agent.
2. If no image tool exists, run `python3 scripts/setup.py` and follow its prompts.
3. If the configured mode is `agent_tool`, return image prompts when the current agent cannot generate images.
4. For API mode, write the page plan to JSON and run `python3 scripts/generate.py --plan <plan.json> --output <directory>`.

Never request or reveal a provider key in chat. Let `setup.py` collect it locally. Never print secrets or include them in generated artifacts.

## Create the post

Run this as a two-turn workflow. Never combine outline approval and image generation in the same turn unless the user explicitly says to skip confirmation or generate directly.

### Phase 1: Propose and confirm the outline

1. Preserve the user's original topic, draft and detailed instructions in a UTF-8 topic file. Do not summarize or rewrite them before generation.
2. Run `python3 scripts/generate_outline.py --topic-file <topic.txt> --output <outline.json>`. Add each ordinary reference with `--image <path>` and each product input with `--product-image <path>`.
3. The script must load `assets/outline_prompt.txt`, call the configured text model, pass reference images as multimodal inputs, and parse the model response using the original `<page>` delimiter. Do not substitute Codex-authored planning for this call.
4. Present `outline.json.outline` in full, preserving every page's detailed copy and image suggestion. Add page headings for readability, but do not compress it into a summary table.
5. End the turn by asking the user to confirm the detailed outline or name the pages to change. Do not create images or final publication copy yet.
6. Treat replies such as “确认”“可以”“开始生成”“按这个来” as approval. If the user requests changes, preserve the remaining raw page content, edit only the requested pages, and ask for confirmation again.

### Phase 2: Create after approval

1. Read [references/copywriting-rules.md](references/copywriting-rules.md) and write the publication copy.
2. Read [references/image-prompt-rules.md](references/image-prompt-rules.md), then build a page plan matching [references/output-schema.md](references/output-schema.md).
3. Validate the plan with `python3 scripts/validate_plan.py <plan.json>`.
4. For API generation, always use `scripts/generate.py`; it loads the bundled high-fidelity prompt from `assets/image_prompt.txt`, injects the full outline and user topic, generates the cover first, and passes that cover as `@封面参考图` to every later Gemini request.
5. Generate the remaining pages in page order. Preserve successful pages if one page fails; retry only the failed or visibly defective page once.
6. Visually inspect every generated page for missing pages, unreadable text, invented text and obvious style drift.
7. Deliver the selected title, alternatives, body, tags, plan JSON, and numbered images. If images are unavailable, clearly deliver reusable per-page prompts instead.

## Display the finished work

The final response must display every successfully generated page inline and in page order using Markdown image syntax with absolute paths. Do not show only the cover, a directory link, or a contact sheet.

Use this layout:

```markdown
### 第1页｜封面
![第1页 封面](/absolute/path/01-cover.png)

### 第2页｜内容
![第2页 内容](/absolute/path/02-content.png)
```

After all page images, provide links to the publication copy, plan JSON and output directory. If a page failed, keep its position in the sequence and state the failure directly below that page heading.

## Defaults

- Use Chinese and target Xiaohongshu unless requested otherwise.
- Create 6–8 pages: one cover, concise content pages, and an optional summary/action page.
- Use a vertical 3:4 canvas and mobile-readable text.
- Keep claims grounded in user material or common knowledge. Do not invent statistics, certifications, efficacy, testimonials, prices, or endorsements.
- Treat ordinary references as style, composition, atmosphere and layout inspiration.
- Treat product images as identity-bearing source material. Preserve packaging, color, shape and recognizable product details.
- Put shared input paths in `brief.reference_images` and `brief.product_images`; put page-specific inputs in the same fields on each page. The API pipeline maps and sends them as multimodal inputs.
- Do not reproduce watermarks, account IDs or platform logos from references.
- Ask for confirmation before publishing or sending content externally. Creation alone does not authorize publication.

## Handle limitations

- If a model cannot render reliable Chinese text, generate clean backgrounds/illustrations and provide an exact text overlay specification instead of accepting garbled text.
- If a provider cannot use reference images, explain that product identity cannot be guaranteed and offer prompt-only or background-only output.
- If setup is incomplete, run `python3 scripts/setup.py --status` and give the user the single next action it reports.
