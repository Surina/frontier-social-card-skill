# 输出结构

将创作计划保存为 UTF-8 JSON：

```json
{
  "version": 1,
  "brief": {
    "topic": "主题",
    "platform": "xiaohongshu",
    "audience": "目标人群",
    "goal": "内容目标",
    "tone": "表达风格",
    "visual_style": "视觉风格",
    "aspect_ratio": "3:4",
    "reference_images": [],
    "product_images": []
  },
  "post": {
    "selected_title": "主标题",
    "alternative_titles": ["备选一", "备选二"],
    "body": "发布正文",
    "tags": ["标签一", "标签二"]
  },
  "pages": [
    {
      "index": 1,
      "type": "cover",
      "headline": "画面标题",
      "body": ["副标题或要点"],
      "visual": "画面说明",
      "text_overlay": ["必须显示的文字"],
      "reference_images": [],
      "product_images": [],
      "image_prompt": "独立完整的图片提示词"
    }
  ]
}
```

图片文件使用两位页码：`01-cover.png`、`02-content.png`。即使生成部分失败，也保留计划和成功图片，并记录失败页。

## 对话交付阶段

生成前先展示人类可读的大纲并等待明确确认。大纲确认前不得调用图片模型。

生成完成后必须按页码顺序内联展示所有图片；文件夹链接只能作为补充，不能替代逐页展示。
