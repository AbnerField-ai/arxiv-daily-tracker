# arXiv 每日论文追踪器

自动追踪 AI 前沿论文，每天生成结构化摘要网页，筛选优质信息。

## 关注方向

- 🌍 世界模型 (World Model)
- 🎨 多模态 (Multimodal / VLM)
- 🧠 大模型 (LLM / Foundation Model)
- 🤖 Agent (AI Agent / Tool Use)
- 🦾 具身智能 (Embodied AI)

## 工作原理

1. 每天北京时间 8:00，GitHub Actions 自动运行
2. 从 arXiv 抓取相关领域最新论文
3. 用 DeepSeek API 进行筛选和结构化摘要
4. 生成网页部署到 GitHub Pages

## 查看方式

部署成功后，访问：`https://你的用户名.github.io/arxiv-daily-tracker/`
