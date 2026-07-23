"""
将 JSON 数据渲染为四板块可浏览的 HTML 论文日报网页
板块4(置顶): 今日趋势总结
板块3: 大厂动态（深色风格）
板块1: 全部精选论文（白底蓝调）
板块2: 联系人库（底部）
"""

import json
import os
from datetime import datetime
from pathlib import Path


def generate_html(data_file, output_file):
    """读取 JSON 数据，生成四板块 HTML 页面"""

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    papers = data.get("papers", [])
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    total_fetched = data.get("total_fetched", 0)
    total_matched = data.get("total_matched", 0)
    org_analysis = data.get("org_analysis", [])
    contacts = data.get("contacts", [])
    daily_insight = data.get("daily_insight", {})
    key_lab_papers = data.get("key_lab_papers", [])
    key_labs_list = data.get("key_labs_list", [])

    # ============ 板块4：今日趋势总结 ============
    insight_html = ""
    if daily_insight and daily_insight.get("hot_topics"):
        hot_topics = daily_insight.get("hot_topics", "")
        lab_overlap = daily_insight.get("lab_overlap", "")
        signals = daily_insight.get("signals", "")
        overlap_labs = daily_insight.get("overlap_labs", [])
        overlap_topic = daily_insight.get("overlap_topic", "")

        # 高亮标签
        overlap_badges = ""
        if overlap_labs:
            badges = " ".join([f'<span class="overlap-badge">{lab}</span>' for lab in overlap_labs])
            overlap_badges = f'<div class="overlap-tags">{badges}'
            if overlap_topic:
                overlap_badges += f' <span class="overlap-topic">→ {overlap_topic}</span>'
            overlap_badges += '</div>'

        insight_html = f"""
    <div class="section-insight">
        <div class="insight-header">
            <h2>今日趋势总结</h2>
            <span class="insight-date">{date}</span>
        </div>
        <div class="insight-body">
            <div class="insight-item">
                <div class="insight-label">研究热点</div>
                <div class="insight-content">{hot_topics}</div>
            </div>
            <div class="insight-item highlight">
                <div class="insight-label">大厂方向重合</div>
                <div class="insight-content">{lab_overlap}</div>
                {overlap_badges}
            </div>
            <div class="insight-item">
                <div class="insight-label">值得关注</div>
                <div class="insight-content">{signals}</div>
            </div>
        </div>
    </div>
"""

    # ============ 板块3：大厂动态 ============
    labs_html = ""
    if key_lab_papers:
        # 按机构分组
        lab_groups = {}
        for paper in key_lab_papers:
            for org in paper.get("identified_orgs", []):
                if org in key_labs_list:
                    if org not in lab_groups:
                        lab_groups[org] = []
                    lab_groups[org].append(paper)

        labs_html += '<div class="section-labs">\n'
        labs_html += '    <h2 class="labs-title">大厂动态 <span class="labs-count">'
        labs_html += f'{len(key_lab_papers)} 篇来自重点机构</span></h2>\n'

        for org_name in key_labs_list:
            if org_name not in lab_groups:
                continue
            org_papers = lab_groups[org_name]
            labs_html += f"""
        <div class="lab-group">
            <div class="lab-header">
                <span class="lab-name">{org_name}</span>
                <span class="lab-badge">{len(org_papers)} 篇</span>
            </div>
"""
            for paper in org_papers:
                summary = paper.get("ai_summary", {})
                score = summary.get("score", 5)
                score_class = "high" if score >= 8 else "medium" if score >= 6 else "low"
                topics_str = " / ".join(paper.get("matched_topics", []))
                labs_html += f"""
            <div class="lab-paper">
                <div class="lab-paper-header">
                    <span class="score {score_class}">{score}/10</span>
                    <span class="lab-paper-topics">{topics_str}</span>
                </div>
                <h4 class="lab-paper-title">
                    <a href="{paper.get('url', '#')}" target="_blank">{paper.get('title', '无标题')}</a>
                </h4>
                <div class="lab-paper-summary">
                    <span><strong>方法：</strong>{summary.get('method', '—')}</span>
                    <span><strong>创新：</strong>{summary.get('novelty', '—')}</span>
                </div>
                <a href="{paper.get('pdf', '#')}" target="_blank" class="lab-pdf-link">PDF 原文</a>
            </div>
"""
            labs_html += "        </div>\n"
        labs_html += "    </div>\n"

    # ============ 板块1：全部精选论文 ============
    # 按方向分组
    topic_groups = {}
    for paper in papers:
        for topic in paper.get("matched_topics", ["其他"]):
            if topic not in topic_groups:
                topic_groups[topic] = []
            topic_groups[topic].append(paper)

    topic_order = ["世界模型", "多模态", "大模型", "Agent", "具身智能"]
    sorted_topics = sorted(
        topic_groups.keys(),
        key=lambda x: topic_order.index(x) if x in topic_order else 99,
    )

    cards_html = ""
    for topic in sorted_topics:
        topic_papers = topic_groups[topic]
        cards_html += f'<h3 class="topic-header">{topic} <span class="count">({len(topic_papers)} 篇)</span></h3>\n'

        for paper in topic_papers:
            summary = paper.get("ai_summary", {})
            score = summary.get("score", 5)
            score_class = "high" if score >= 8 else "medium" if score >= 6 else "low"
            authors_str = ", ".join(paper.get("authors", [])[:3])
            if len(paper.get("authors", [])) > 3:
                authors_str += " et al."
            orgs = paper.get("identified_orgs", [])
            org_tag = f'<span class="org-tag">{" / ".join(orgs)}</span>' if orgs else ""

            cards_html += f"""
        <div class="paper-card" data-score="{score}">
            <div class="card-header">
                <span class="score {score_class}">{score}/10</span>
                {org_tag}
                <span class="date">{paper.get('published', '')}</span>
            </div>
            <h4 class="paper-title">
                <a href="{paper.get('url', '#')}" target="_blank">{paper.get('title', '无标题')}</a>
            </h4>
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

    # ============ 板块2：联系人库 ============
    contacts_html = ""
    if contacts:
        # 分为大厂联系人和普通联系人
        key_contacts = [c for c in contacts if c.get("is_key_lab", False)]
        other_contacts = [c for c in contacts if not c.get("is_key_lab", False)]

        contacts_html += '<div class="section-contacts">\n'
        contacts_html += '    <h2 class="contacts-title">联系人库 <span class="contacts-count">'
        contacts_html += f'{len(contacts)} 位作者</span></h2>\n'

        # 大厂联系人（橙色高亮）
        if key_contacts:
            contacts_html += '    <h3 class="contacts-subtitle key-lab-subtitle">重点机构作者</h3>\n'
            for entry in key_contacts:
                contacts_html += _render_contact_card(entry, is_key_lab=True)

        # 其他联系人
        if other_contacts:
            contacts_html += '    <h3 class="contacts-subtitle">其他作者</h3>\n'
            for entry in other_contacts:
                contacts_html += _render_contact_card(entry, is_key_lab=False)

        contacts_html += '</div>\n'

    # 生成历史归档链接
    data_dir = Path(data_file).parent
    archive_links = ""
    json_files = sorted(data_dir.glob("2*.json"), reverse=True)[:30]
    for jf in json_files:
        d = jf.stem
        archive_links += f'<a href="{d}.html" class="archive-link">{d}</a>\n'

    # ============ 组装完整 HTML ============
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
            background: #f0f2f5;
            color: #333;
            line-height: 1.6;
        }}

        /* ====== 页头 ====== */
        .page-header {{
            text-align: center;
            padding: 30px 20px;
            background: white;
            border-bottom: 1px solid #e5e7eb;
        }}
        .page-header h1 {{
            font-size: 1.8em;
            color: #1a1a2e;
            margin-bottom: 6px;
        }}
        .page-header .meta {{
            color: #666;
            font-size: 0.9em;
        }}
        .stats {{
            display: flex;
            gap: 16px;
            justify-content: center;
            margin-top: 12px;
            flex-wrap: wrap;
        }}
        .stat {{
            background: #f8f9fa;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.82em;
            color: #555;
        }}

        /* ====== 导航 ====== */
        .nav-bar {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: white;
            border-bottom: 1px solid #e5e7eb;
            padding: 10px 20px;
            display: flex;
            gap: 12px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        .nav-bar a {{
            text-decoration: none;
            font-size: 0.85em;
            padding: 5px 14px;
            border-radius: 16px;
            color: #555;
            background: #f3f4f6;
            transition: all 0.2s;
        }}
        .nav-bar a:hover {{ background: #4a6cf7; color: white; }}
        .nav-bar a.nav-labs {{ background: #1e293b; color: #94a3b8; }}
        .nav-bar a.nav-labs:hover {{ background: #334155; color: white; }}

        /* ====== 板块4: 趋势总结 ====== */
        .section-insight {{
            max-width: 900px;
            margin: 24px auto;
            padding: 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            color: white;
        }}
        .insight-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        .insight-header h2 {{
            font-size: 1.3em;
        }}
        .insight-date {{
            opacity: 0.8;
            font-size: 0.85em;
        }}
        .insight-body {{
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}
        .insight-item {{
            background: rgba(255,255,255,0.12);
            border-radius: 10px;
            padding: 14px 16px;
        }}
        .insight-item.highlight {{
            background: rgba(255,255,255,0.22);
            border: 1px solid rgba(255,255,255,0.3);
        }}
        .insight-label {{
            font-size: 0.78em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            opacity: 0.8;
            margin-bottom: 4px;
        }}
        .insight-content {{
            font-size: 0.92em;
            line-height: 1.5;
        }}
        .overlap-tags {{
            margin-top: 8px;
        }}
        .overlap-badge {{
            display: inline-block;
            background: #fbbf24;
            color: #1a1a2e;
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 0.78em;
            font-weight: 600;
            margin-right: 6px;
        }}
        .overlap-topic {{
            font-size: 0.82em;
            opacity: 0.9;
        }}

        /* ====== 板块3: 大厂动态 ====== */
        .section-labs {{
            max-width: 900px;
            margin: 24px auto;
            padding: 24px;
            background: #1e293b;
            border-radius: 16px;
            color: #e2e8f0;
        }}
        .labs-title {{
            font-size: 1.3em;
            color: white;
            margin-bottom: 20px;
        }}
        .labs-count {{
            font-size: 0.6em;
            font-weight: normal;
            color: #94a3b8;
        }}
        .lab-group {{
            margin-bottom: 20px;
        }}
        .lab-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
            padding-bottom: 6px;
            border-bottom: 1px solid #334155;
        }}
        .lab-name {{
            font-size: 1.05em;
            font-weight: 600;
            color: #f1f5f9;
        }}
        .lab-badge {{
            background: #3b82f6;
            color: white;
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 0.75em;
        }}
        .lab-paper {{
            background: #293548;
            border-radius: 10px;
            padding: 14px 16px;
            margin-bottom: 10px;
        }}
        .lab-paper-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        }}
        .lab-paper-topics {{
            font-size: 0.8em;
            color: #94a3b8;
        }}
        .lab-paper-title {{
            font-size: 0.95em;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        .lab-paper-title a {{
            color: #e2e8f0;
            text-decoration: none;
        }}
        .lab-paper-title a:hover {{
            color: #60a5fa;
            text-decoration: underline;
        }}
        .lab-paper-summary {{
            display: flex;
            flex-direction: column;
            gap: 4px;
            font-size: 0.85em;
            color: #94a3b8;
            margin-bottom: 8px;
        }}
        .lab-paper-summary strong {{
            color: #cbd5e1;
        }}
        .lab-pdf-link {{
            color: #60a5fa;
            text-decoration: none;
            font-size: 0.82em;
        }}
        .lab-pdf-link:hover {{ text-decoration: underline; }}

        /* ====== 板块1: 全部论文 ====== */
        .section-papers {{
            max-width: 900px;
            margin: 24px auto;
            padding: 24px;
            background: white;
            border-radius: 16px;
        }}
        .papers-title {{
            font-size: 1.3em;
            color: #1a1a2e;
            margin-bottom: 20px;
        }}
        .topic-header {{
            font-size: 1.15em;
            color: #1a1a2e;
            margin: 24px 0 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .topic-header .count {{
            font-size: 0.7em;
            color: #888;
            font-weight: normal;
        }}
        .paper-card {{
            background: #f8fafc;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 14px;
            border: 1px solid #e5e7eb;
            transition: box-shadow 0.2s;
        }}
        .paper-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        .card-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
            flex-wrap: wrap;
        }}
        .score {{
            font-weight: bold;
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 0.82em;
        }}
        .score.high {{ background: #d1fae5; color: #065f46; }}
        .score.medium {{ background: #fef3c7; color: #92400e; }}
        .score.low {{ background: #f3f4f6; color: #6b7280; }}
        .org-tag {{
            background: #ede9fe;
            color: #6d28d9;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.75em;
        }}
        .date {{ color: #9ca3af; font-size: 0.82em; margin-left: auto; }}
        .paper-title {{
            font-size: 0.98em;
            margin-bottom: 4px;
            line-height: 1.4;
        }}
        .paper-title a {{
            color: #1e293b;
            text-decoration: none;
        }}
        .paper-title a:hover {{
            color: #4a6cf7;
            text-decoration: underline;
        }}
        .authors {{
            color: #6b7280;
            font-size: 0.82em;
            margin-bottom: 10px;
        }}
        .summary {{
            background: white;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            border: 1px solid #f1f5f9;
        }}
        .summary-item {{
            margin-bottom: 4px;
            font-size: 0.85em;
            color: #4b5563;
        }}
        .summary-item:last-child {{ margin-bottom: 0; }}
        .summary-item strong {{ color: #374151; }}
        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .topics {{ color: #9ca3af; font-size: 0.78em; }}
        .pdf-link {{
            color: #4a6cf7;
            text-decoration: none;
            font-size: 0.82em;
            font-weight: 500;
        }}
        .pdf-link:hover {{ text-decoration: underline; }}

        /* ====== 板块2: 联系人库 ====== */
        .section-contacts {{
            max-width: 900px;
            margin: 24px auto;
            padding: 24px;
            background: white;
            border-radius: 16px;
        }}
        .contacts-title {{
            font-size: 1.3em;
            color: #1a1a2e;
            margin-bottom: 16px;
        }}
        .contacts-count {{
            font-size: 0.6em;
            font-weight: normal;
            color: #888;
        }}
        .contacts-subtitle {{
            font-size: 1em;
            color: #555;
            margin: 16px 0 10px;
            padding-bottom: 6px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .key-lab-subtitle {{
            color: #ea580c;
        }}
        .contact-card {{
            background: #f8fafc;
            border-radius: 8px;
            padding: 12px 14px;
            margin-bottom: 10px;
            border: 1px solid #e5e7eb;
        }}
        .contact-card.key-lab {{
            background: #fff7ed;
            border-color: #fed7aa;
        }}
        .contact-paper {{
            margin-bottom: 6px;
        }}
        .contact-paper a {{
            color: #1e293b;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.88em;
        }}
        .contact-paper a:hover {{ color: #4a6cf7; text-decoration: underline; }}
        .contact-org-badge {{
            display: inline-block;
            background: #ea580c;
            color: white;
            padding: 1px 8px;
            border-radius: 4px;
            font-size: 0.72em;
            margin-left: 6px;
        }}
        .contact-org-badge.normal {{
            background: #6b7280;
        }}
        .contact-list {{
            padding-left: 10px;
            border-left: 3px solid #fed7aa;
        }}
        .contact-card:not(.key-lab) .contact-list {{
            border-left-color: #e5e7eb;
        }}
        .contact-person {{
            font-size: 0.84em;
            margin-bottom: 3px;
            color: #374151;
        }}
        .email-link {{
            color: #ea580c;
            text-decoration: none;
            font-size: 0.84em;
        }}
        .contact-card:not(.key-lab) .email-link {{
            color: #4a6cf7;
        }}
        .email-link:hover {{ text-decoration: underline; }}
        .role-badge {{
            display: inline-block;
            background: #fef3c7;
            color: #92400e;
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 0.72em;
            margin-right: 4px;
        }}
        .corresponding {{
            font-size: 0.78em;
            color: #9ca3af;
            margin-top: 4px;
            font-style: italic;
        }}

        /* ====== 底部归档 ====== */
        .section-archive {{
            max-width: 900px;
            margin: 24px auto;
            padding: 20px 24px;
            background: white;
            border-radius: 16px;
        }}
        .archive h2 {{ font-size: 1em; margin-bottom: 10px; color: #666; }}
        .back-latest {{
            display: inline-block;
            margin-bottom: 12px;
            padding: 6px 16px;
            background: #4a6cf7;
            color: white;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.88em;
            font-weight: 500;
        }}
        .back-latest:hover {{ background: #3a5ce5; }}
        .archive-link {{
            display: inline-block;
            margin: 4px 8px 4px 0;
            padding: 4px 12px;
            background: #f3f4f6;
            border-radius: 6px;
            text-decoration: none;
            color: #4a6cf7;
            font-size: 0.82em;
        }}
        .archive-link:hover {{ background: #e5e7eb; }}

        .empty-state {{
            text-align: center;
            padding: 50px 20px;
            color: #9ca3af;
        }}

        @media (max-width: 640px) {{
            .section-insight, .section-labs, .section-papers, .section-contacts, .section-archive {{
                margin: 12px 8px;
                padding: 16px;
                border-radius: 12px;
            }}
            .page-header h1 {{ font-size: 1.4em; }}
            .stats {{ gap: 8px; }}
            .nav-bar {{ gap: 6px; padding: 8px 12px; }}
        }}
    </style>
</head>
<body>
    <div class="page-header">
        <h1>AI 论文日报</h1>
        <p class="meta">{date} | 世界模型 / 多模态 / 大模型 / Agent / 具身智能</p>
        <div class="stats">
            <span class="stat">arXiv 抓取 {total_fetched} 篇</span>
            <span class="stat">AI 筛选 {total_matched} 篇</span>
            <span class="stat">大厂论文 {len(key_lab_papers)} 篇</span>
            <span class="stat">联系人 {len(contacts)} 位</span>
        </div>
    </div>

    <nav class="nav-bar">
        <a href="#insight">趋势总结</a>
        <a href="#labs" class="nav-labs">大厂动态</a>
        <a href="#papers">全部论文</a>
        <a href="#contacts">联系人库</a>
    </nav>

    <div id="insight">
    {insight_html if insight_html else '<div class="section-insight"><p style="opacity:0.8">今日暂无趋势分析</p></div>'}
    </div>

    <div id="labs">
    {labs_html if labs_html else '<div class="section-labs"><p style="color:#94a3b8">今日暂无大厂论文</p></div>'}
    </div>

    <div id="papers">
    <div class="section-papers">
        <h2 class="papers-title">全部精选论文</h2>
        {"<div class='empty-state'><p>今天没有匹配到相关论文</p></div>" if not papers else cards_html}
    </div>
    </div>

    <div id="contacts">
    {contacts_html if contacts_html else '<div class="section-contacts"><p style="color:#9ca3af">今日暂无联系人信息</p></div>'}
    </div>

    <div class="section-archive">
        <div class="archive">
            <a href="index.html" class="back-latest">← 返回最新日报</a>
            <h2>历史归档</h2>
            {archive_links if archive_links else '<p style="color:#9ca3af;font-size:0.85em;">暂无历史数据</p>'}
        </div>
    </div>
</body>
</html>"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[网页] 已生成: {output_file}")


def _render_contact_card(entry, is_key_lab=False):
    """渲染单个联系人卡片"""
    paper_title = entry.get("paper_title", "")[:60]
    paper_url = entry.get("paper_url", "#")
    paper_score = entry.get("paper_score", 0)
    orgs = entry.get("orgs", [])
    emails = entry.get("emails", [])
    ai_contacts = entry.get("contacts", [])
    corresponding = entry.get("corresponding_author", "")

    card_class = "contact-card key-lab" if is_key_lab else "contact-card"
    badge_class = "contact-org-badge" if is_key_lab else "contact-org-badge normal"

    html = f"""
        <div class="{card_class}">
            <div class="contact-paper">
                <a href="{paper_url}" target="_blank">[{paper_score}分] {paper_title}{"..." if len(entry.get("paper_title", "")) > 60 else ""}</a>
                {f'<span class="{badge_class}">{" / ".join(orgs)}</span>' if orgs else ''}
            </div>
"""
    if ai_contacts:
        html += '            <div class="contact-list">\n'
        for c in ai_contacts[:5]:
            name = c.get("name", "")
            email = c.get("email", "")
            aff = c.get("affiliation", "")
            role = c.get("role", "")
            role_badge = f'<span class="role-badge">{role}</span>' if role else ""
            email_link = f'<a href="mailto:{email}" class="email-link">{email}</a>' if email else ""
            html += f'                <div class="contact-person">{role_badge}<strong>{name}</strong> {f"— {aff}" if aff else ""} {email_link}</div>\n'
        html += '            </div>\n'
    elif emails:
        html += '            <div class="contact-list">\n'
        for email in emails[:5]:
            html += f'                <div class="contact-person"><a href="mailto:{email}" class="email-link">{email}</a></div>\n'
        html += '            </div>\n'

    if corresponding:
        html += f'            <div class="corresponding">通讯作者: {corresponding}</div>\n'

    html += "        </div>\n"
    return html


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

    print("[完成] 网页生成完毕")


if __name__ == "__main__":
    main()
