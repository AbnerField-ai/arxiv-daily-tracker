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
    org_analysis = data.get("org_analysis", [])
    contacts = data.get("contacts", [])

    # 生成机构分析板块
    org_html = ""
    if org_analysis:
        org_html += '<div class="org-section">\n'
        org_html += '<h2 class="topic-header">机构布局 <span class="count">(今日活跃)</span></h2>\n'
        for org_data in org_analysis:
            org_name = org_data["org"]
            count = org_data["count"]
            topics = org_data.get("topics", {})
            topic_tags = " / ".join([f"{t}({n})" for t, n in topics.items()])
            paper_titles = org_data.get("papers", [])

            org_html += f"""
        <div class="org-card">
            <div class="org-header">
                <span class="org-name">{org_name}</span>
                <span class="org-count">{count} 篇</span>
            </div>
            <div class="org-topics">{topic_tags}</div>
            <div class="org-papers">
"""
            for p in paper_titles[:3]:
                score = p.get("score", 5)
                org_html += f'                <a href="{p.get("url", "#")}" target="_blank" class="org-paper-link">[{score}分] {p["title"][:60]}{"..." if len(p["title"]) > 60 else ""}</a>\n'
            org_html += "            </div>\n        </div>\n"
        org_html += "</div>\n"

    # 生成联系人/关键人物板块
    contacts_html = ""
    if contacts:
        contacts_html += '<div class="contacts-section">\n'
        contacts_html += '<h2 class="topic-header">关键人物 <span class="count">(今日高分论文作者)</span></h2>\n'
        for entry in contacts:
            paper_title = entry.get("paper_title", "")[:50]
            paper_url = entry.get("paper_url", "#")
            paper_score = entry.get("paper_score", 0)
            orgs = entry.get("orgs", [])
            emails = entry.get("emails", [])
            ai_contacts = entry.get("contacts", [])
            corresponding = entry.get("corresponding_author", "")

            contacts_html += f"""
        <div class="contact-card">
            <div class="contact-paper">
                <a href="{paper_url}" target="_blank">[{paper_score}分] {paper_title}{"..." if len(entry.get("paper_title", "")) > 50 else ""}</a>
                {f'<span class="contact-org">{" / ".join(orgs)}</span>' if orgs else ''}
            </div>
"""
            if ai_contacts:
                contacts_html += '            <div class="contact-list">\n'
                for c in ai_contacts[:5]:
                    name = c.get("name", "")
                    email = c.get("email", "")
                    aff = c.get("affiliation", "")
                    role = c.get("role", "")
                    role_badge = f'<span class="role-badge">{role}</span>' if role else ""
                    email_link = f'<a href="mailto:{email}" class="email-link">{email}</a>' if email else ""
                    contacts_html += f'                <div class="contact-person">{role_badge}<strong>{name}</strong> {f"— {aff}" if aff else ""} {email_link}</div>\n'
                contacts_html += '            </div>\n'
            elif emails:
                contacts_html += '            <div class="contact-list">\n'
                for email in emails[:5]:
                    contacts_html += f'                <div class="contact-person"><a href="mailto:{email}" class="email-link">{email}</a></div>\n'
                contacts_html += '            </div>\n'

            if corresponding:
                contacts_html += f'            <div class="corresponding">通讯作者: {corresponding}</div>\n'

            contacts_html += "        </div>\n"
        contacts_html += "</div>\n"

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
        .back-latest {{
            display: inline-block;
            margin-bottom: 12px;
            padding: 6px 16px;
            background: #4a6cf7;
            color: white;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.9em;
            font-weight: 500;
        }}
        .back-latest:hover {{ background: #3a5ce5; }}
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
        .org-section {{
            margin: 30px 0;
            padding: 20px;
            background: #f0f4ff;
            border-radius: 12px;
        }}
        .org-card {{
            background: white;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }}
        .org-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}
        .org-name {{
            font-weight: bold;
            font-size: 1.05em;
            color: #1a1a2e;
        }}
        .org-count {{
            background: #4a6cf7;
            color: white;
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 0.8em;
        }}
        .org-topics {{
            color: #666;
            font-size: 0.85em;
            margin-bottom: 8px;
        }}
        .org-papers {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .org-paper-link {{
            color: #4a6cf7;
            text-decoration: none;
            font-size: 0.82em;
            padding: 2px 0;
        }}
        .org-paper-link:hover {{ text-decoration: underline; }}
        .contacts-section {{
            margin: 30px 0;
            padding: 20px;
            background: #fff8f0;
            border-radius: 12px;
        }}
        .contact-card {{
            background: white;
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 10px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }}
        .contact-paper {{
            margin-bottom: 8px;
        }}
        .contact-paper a {{
            color: #1a1a2e;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.9em;
        }}
        .contact-paper a:hover {{ color: #4a6cf7; text-decoration: underline; }}
        .contact-org {{
            color: #888;
            font-size: 0.8em;
            margin-left: 8px;
        }}
        .contact-list {{
            padding-left: 12px;
            border-left: 3px solid #ffe0b2;
        }}
        .contact-person {{
            font-size: 0.85em;
            margin-bottom: 4px;
            color: #333;
        }}
        .email-link {{
            color: #e67e22;
            text-decoration: none;
            font-size: 0.85em;
        }}
        .email-link:hover {{ text-decoration: underline; }}
        .role-badge {{
            display: inline-block;
            background: #ffe0b2;
            color: #e65100;
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 0.75em;
            margin-right: 4px;
        }}
        .corresponding {{
            font-size: 0.8em;
            color: #888;
            margin-top: 6px;
            font-style: italic;
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

    {org_html}

    {contacts_html}

    {"<div class='empty-state'><p>今天没有匹配到相关论文</p></div>" if not papers else cards_html}

    <div class="archive">
        <a href="index.html" class="back-latest">← 返回最新日报</a>
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
