# 输出结构

图片生成直接使用 `generate_outline.py` 输出的 UTF-8 JSON：

```json
{
  "success": true,
  "topic": "用户原始主题或全文",
  "outline": "[封面]\\n...\\n<page>\\n[内容]\\n...",
  "reference_images": [],
  "product_images": [],
  "pages": [
    {
      "index": 1,
      "type": "cover",
      "content": "[封面]\\n标题：..."
    }
  ]
}
```

不要为了图片生成创建第二份页面计划。发布文案可以单独保存，但不得反向改写 `pages[].content`。

图片文件使用两位页码：`01-cover.png`、`02-content.png`。即使生成部分失败，也保留计划和成功图片，并记录失败页。

## 对话交付阶段

生成前先展示人类可读的大纲并等待明确确认。大纲确认前不得调用图片模型。

生成完成后必须按页码顺序内联展示所有图片；文件夹链接只能作为补充，不能替代逐页展示。
