"""
将 JSON 数据渲染为可浏览的 HTML 论文日报网页
"""

import json
import os
from datetime import datetime
from pathlib import Path


def generate_html(data_file, output_file):
    """读取 JSON 数据，生成 HTML 页面"""

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    papers = data.get("papers", [])
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    total_fetched = data.get("total_fetched", 0)
    total_matched = data.get("total_matched", 0)

    # 按方向分组
    topic_groups = {}
    for paper in papers:
        for topic in paper.get("matched_topics", ["其他"]):
            if topic not in topic_groups:
                topic_groups[topic] = []
            topic_groups[topic].append(paper)

    # 优先级排序
    topic_order = ["世界模型", "多模态", "大模型", "Agent", "具身智能"]
    sorted_topics = sorted(
        topic_groups.keys(),
        key=lambda x: topic_order.index(x) if x in topic_order else 99,
    )

    # 生成论文卡片 HTML
    cards_html = ""
    for topic in sorted_topics:
        topic_papers = topic_groups[topic]
        cards_html += f'<h2 class="topic-header">{topic} <span class="count">({len(topic_papers)} 篇)</span></h2>\n'

        for paper in topic_papers:
            summary = paper.get("ai_summary", {})
            score = summary.get("score", 5)
            score_class = "high" if score >= 8 else "medium" if score >= 6 else "low"
            authors_str = ", ".join(paper.get("authors", [])[:3])
            if len(paper.get("authors", [])) > 3:
                authors_str += " et al."

            cards_html += f"""
        <div class="paper-card" data-score="{score}">
            <div class="card-header">
                <span class="score {score_class}">{score}/10</span>
                <span class="date">{paper.get('published', '')}</span>
            </div>
            <h3 class="paper-title">
                <a href="{paper.get('url', '#')}" target="_blank">{paper.get('title', '无标题')}</a>
            </h3>
            <p class="authors">{authors_str}</p>
            <div class="summary">
                <div class="summary-item"><strong>问题：</strong>{summary.get('problem', '—')}</div>
                <div class="summary-item"><strong>方法：</strong>{summary.get('method', '—')}</div>
                <div class="summary-item"><strong>结论：</strong>{summary.get('result', '—')}</div>
                <div class="summary-item"><strong>创新点：</strong>{summary.get('novelty', '—')}</div>
                <div class="summary-item"><strong>意义：</strong>{summary.get('relevance', '—')}</div>
            </div>
            <div class="card-footer">
                <span class="topics">{' / '.join(paper.get('matched_topics', []))}</span>
                <a href="{paper.get('pdf', '#')}" target="_blank" class="pdf-link">PDF 原文</a>
            </div>
        </div>
"""

    # 生成历史归档链接
    data_dir = Path(data_file).parent
    archive_links = ""
    json_files = sorted(data_dir.glob("2*.json"), reverse=True)[:30]
    for jf in json_files:
        d = jf.stem
        archive_links += f'<a href="{d}.html" class="archive-link">{d}</a>\n'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 论文日报 - {date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
            background: #f8f9fa;
            color: #333;
            line-height: 1.6;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid #e9ecef;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 1.8em;
            color: #1a1a2e;
            margin-bottom: 8px;
        }}
        .header .meta {{
            color: #666;
            font-size: 0.9em;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-top: 15px;
        }}
        .stat {{
            background: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85em;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .topic-header {{
            font-size: 1.3em;
            color: #1a1a2e;
            margin: 30px 0 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid #dee2e6;
        }}
        .topic-header .count {{
            font-size: 0.7em;
            color: #888;
            font-weight: normal;
        }}
        .paper-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            transition: box-shadow 0.2s;
        }}
        .paper-card:hover {{
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .score {{
            font-weight: bold;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.85em;
        }}
        .score.high {{ background: #d4edda; color: #155724; }}
        .score.medium {{ background: #fff3cd; color: #856404; }}
        .score.low {{ background: #f8f9fa; color: #666; }}
        .date {{ color: #888; font-size: 0.85em; }}
        .paper-title {{
            font-size: 1.05em;
            margin-bottom: 6px;
            line-height: 1.4;
        }}
        .paper-title a {{
            color: #1a1a2e;
            text-decoration: none;
        }}
        .paper-title a:hover {{
            color: #4a6cf7;
            text-decoration: underline;
        }}
        .authors {{
            color: #666;
            font-size: 0.85em;
            margin-bottom: 12px;
        }}
        .summary {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 12px;
        }}
        .summary-item {{
            margin-bottom: 6px;
            font-size: 0.9em;
        }}
        .summary-item:last-child {{ margin-bottom: 0; }}
        .summary-item strong {{
            color: #495057;
        }}
        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .topics {{
            color: #888;
            font-size: 0.8em;
        }}
        .pdf-link {{
            color: #4a6cf7;
            text-decoration: none;
            font-size: 0.85em;
            font-weight: 500;
        }}
        .pdf-link:hover {{ text-decoration: underline; }}
        .archive {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #e9ecef;
        }}
        .archive h2 {{ font-size: 1.1em; margin-bottom: 10px; color: #666; }}
        .archive-link {{
            display: inline-block;
            margin: 4px 8px 4px 0;
            padding: 4px 12px;
            background: white;
            border-radius: 6px;
            text-decoration: none;
            color: #4a6cf7;
            font-size: 0.85em;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }}
        @media (max-width: 600px) {{
            body {{ padding: 12px; }}
            .header h1 {{ font-size: 1.4em; }}
            .stats {{ flex-direction: column; align-items: center; gap: 8px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI 论文日报</h1>
        <p class="meta">{date} | 关注方向：世界模型 / 多模态 / 大模型 / Agent / 具身智能</p>
        <div class="stats">
            <span class="stat">arXiv 抓取 {total_fetched} 篇</span>
            <span class="stat">AI 筛选 {total_matched} 篇</span>
            <span class="stat">评分 ≥ 6 推荐精读</span>
        </div>
    </div>

    {"<div class='empty-state'><p>今天没有匹配到相关论文</p></div>" if not papers else cards_html}

    <div class="archive">
        <h2>历史归档</h2>
        {archive_links if archive_links else '<p style="color:#888;font-size:0.85em;">暂无历史数据</p>'}
    </div>
</body>
</html>"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[网页] 已生成: {output_file}")


def main():
    """生成网页"""
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    docs_dir = project_root / "docs"
    docs_dir.mkdir(exist_ok=True)

    # 生成最新的 index.html
    latest_file = data_dir / "latest.json"
    if latest_file.exists():
        generate_html(str(latest_file), str(docs_dir / "index.html"))

    # 为每天的数据也生成对应 HTML
    for json_file in data_dir.glob("2*.json"):
        html_file = docs_dir / f"{json_file.stem}.html"
        if not html_file.exists():
            generate_html(str(json_file), str(html_file))

    # 复制数据文件到 docs（供前端可选使用）
    print("[完成] 网页生成完毕")


if __name__ == "__main__":
    main()
