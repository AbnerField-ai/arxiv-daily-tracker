"""
arXiv 每日论文抓取 + DeepSeek AI 筛选摘要
==========================================
功能：
1. 从 arXiv API 抓取指定领域的最新论文
2. 调用 DeepSeek API 对论文进行相关性筛选
3. 为筛选出的论文生成结构化摘要（问题、方法、结论、创新点）
4. 输出 JSON 数据供网页渲染
"""

import os
import json
import time
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ============ 配置区域（你可以修改这里） ============

# 研究方向和关键词（按优先级排列）
TOPICS = {
    "世界模型": {
        "keywords": ["world model", "world models", "world simulator"],
        "priority": 1,  # 数字越小优先级越高
    },
    "多模态": {
        "keywords": ["multimodal", "vision-language", "VLM", "multi-modal", "visual language model"],
        "priority": 1,
    },
    "大模型": {
        "keywords": ["large language model", "LLM", "foundation model", "GPT", "language model scaling"],
        "priority": 2,
    },
    "Agent": {
        "keywords": ["AI agent", "LLM agent", "autonomous agent", "tool use", "agentic"],
        "priority": 2,
    },
    "具身智能": {
        "keywords": ["embodied AI", "embodied intelligence", "robot learning", "embodied agent"],
        "priority": 2,
    },
}

# arXiv 分类（覆盖 AI 相关领域）
ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.RO", "cs.MA"]

# 每天最多处理的论文数（控制 API 调用成本）
MAX_PAPERS_TO_SUMMARIZE = 20

# DeepSeek API 配置
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"  # 可改为 deepseek-reasoner 等

# 已知机构关键词（用于从作者署名中识别机构）
KNOWN_ORGS = {
    # 国际大厂
    "Google": ["google", "deepmind", "google deepmind", "google research"],
    "Meta": ["meta", "fair", "meta ai", "facebook"],
    "OpenAI": ["openai"],
    "Microsoft": ["microsoft", "microsoft research", "msra"],
    "Apple": ["apple"],
    "NVIDIA": ["nvidia"],
    "Amazon": ["amazon", "aws", "alexa"],
    "Tesla": ["tesla"],
    # 中国公司
    "字节跳动": ["bytedance", "douyin", "tiktok"],
    "腾讯": ["tencent"],
    "阿里巴巴": ["alibaba", "damo academy", "aliyun", "tongyi"],
    "百度": ["baidu"],
    "华为": ["huawei"],
    "商汤": ["sensetime"],
    "智谱AI": ["zhipu", "glm", "thudm"],
    "DeepSeek": ["deepseek"],
    "月之暗面": ["moonshot", "kimi"],
    # 顶尖高校
    "MIT": ["mit", "massachusetts institute of technology"],
    "Stanford": ["stanford"],
    "CMU": ["cmu", "carnegie mellon"],
    "UC Berkeley": ["berkeley", "ucb"],
    "清华": ["tsinghua"],
    "北大": ["peking university", "pku"],
    "上海交大": ["shanghai jiao tong"],
}

# ============ 配置结束 ============


def fetch_arxiv_papers(days_back=1):
    """从 arXiv API 获取最近的论文"""

    # 构建搜索查询：所有关键词 OR 连接
    all_keywords = []
    for topic_info in TOPICS.values():
        all_keywords.extend(topic_info["keywords"])

    # arXiv 搜索语法
    keyword_query = " OR ".join([f'all:"{kw}"' for kw in all_keywords])
    cat_query = " OR ".join([f"cat:{cat}" for cat in ARXIV_CATEGORIES])
    query = f"({keyword_query}) AND ({cat_query})"

    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back + 1)  # 多取一天确保不遗漏

    # arXiv API 参数
    params = {
        "search_query": query,
        "start": 0,
        "max_results": 100,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    url = f"http://export.arxiv.org/api/query?{urllib.parse.urlencode(params)}"
    print(f"[抓取] 正在从 arXiv 获取论文...")
    print(f"[抓取] URL: {url[:100]}...")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ArxivDailyTracker/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read().decode("utf-8")
    except Exception as e:
        print(f"[错误] arXiv API 请求失败: {e}")
        return []

    # 解析 XML
    root = ET.fromstring(data)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    papers = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        abstract = entry.find("atom:summary", ns).text.strip().replace("\n", " ")

        # 获取链接
        paper_id = ""
        pdf_link = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                pdf_link = link.get("href")
            elif link.get("rel") == "alternate":
                paper_id = link.get("href")

        # 获取分类
        categories = [cat.get("term") for cat in entry.findall("atom:category", ns)]

        # 获取作者
        authors = [author.find("atom:name", ns).text for author in entry.findall("atom:author", ns)]

        # 获取作者机构信息
        affiliations = []
        for author in entry.findall("atom:author", ns):
            name = author.find("atom:name", ns).text
            affs = [aff.text for aff in author.findall("arxiv:affiliation", ns) if aff.text]
            affiliations.append({"name": name, "affiliations": affs})

        # 获取发布日期
        published = entry.find("atom:published", ns).text[:10]

        papers.append({
            "title": title,
            "abstract": abstract,
            "url": paper_id,
            "pdf": pdf_link,
            "categories": categories,
            "authors": authors[:5],  # 只保留前5位作者
            "all_authors": authors,  # 保留全部作者用于机构分析
            "affiliations": affiliations,
            "published": published,
        })

    print(f"[抓取] 获取到 {len(papers)} 篇论文")
    return papers


def match_topics(paper):
    """判断论文属于哪些研究方向，返回匹配的方向和最高优先级"""
    matched = []
    best_priority = 99

    text = (paper["title"] + " " + paper["abstract"]).lower()

    for topic_name, topic_info in TOPICS.items():
        for keyword in topic_info["keywords"]:
            if keyword.lower() in text:
                matched.append(topic_name)
                best_priority = min(best_priority, topic_info["priority"])
                break

    return matched, best_priority


def call_deepseek(prompt, system_prompt="你是一个AI研究助理。"):
    """调用 DeepSeek API"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("[警告] 未设置 DEEPSEEK_API_KEY，跳过 AI 摘要")
        return None

    payload = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1000,
    })

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        req = urllib.request.Request(DEEPSEEK_API_URL, data=payload.encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[错误] DeepSeek API 调用失败: {e}")
        return None


def filter_and_rank(papers):
    """对论文进行方向匹配和排序"""
    scored_papers = []

    for paper in papers:
        matched_topics, priority = match_topics(paper)
        if matched_topics:
            paper["matched_topics"] = matched_topics
            paper["priority"] = priority
            scored_papers.append(paper)

    # 按优先级排序（数字小的排前面）
    scored_papers.sort(key=lambda x: x["priority"])

    print(f"[筛选] 从 {len(papers)} 篇中匹配到 {len(scored_papers)} 篇相关论文")
    return scored_papers[:MAX_PAPERS_TO_SUMMARIZE]


def generate_summary(paper):
    """为单篇论文生成结构化摘要"""
    prompt = f"""请为以下学术论文生成一份简洁的中文结构化摘要。

标题：{paper['title']}
摘要：{paper['abstract']}
作者及机构：{json.dumps(paper.get('affiliations', [])[:5], ensure_ascii=False)}

请严格按照以下 JSON 格式输出（不要添加任何其他内容）：
{{
    "problem": "这篇论文要解决什么问题（1-2句话）",
    "method": "核心方法是什么（2-3句话）",
    "result": "主要结论/效果（1-2句话）",
    "novelty": "创新点在哪（1句话）",
    "relevance": "对AI领域的意义（1句话）",
    "org": "作者主要来自哪个机构/公司（如能识别）",
    "score": 一个1-10的整数分数，表示这篇论文的重要性和创新性
}}"""

    system_prompt = """你是一位资深的AI研究员，擅长快速阅读和总结学术论文。
你的任务是帮助一位关注AI前沿（特别是世界模型、多模态、大模型、Agent、具身智能）的读者
快速判断一篇论文是否值得深读。
请只输出合法的 JSON，不要输出其他任何文字。"""

    result = call_deepseek(prompt, system_prompt)
    if result:
        # 尝试解析 JSON
        try:
            # 清理可能的 markdown 代码块标记
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            summary = json.loads(cleaned)
            return summary
        except json.JSONDecodeError:
            print(f"[警告] JSON 解析失败，原始输出: {result[:100]}")
            return {"problem": result, "method": "", "result": "", "novelty": "", "relevance": "", "score": 5}
    return None


def identify_org(paper):
    """从论文的机构信息和AI摘要中识别所属机构"""
    identified = set()

    # 方式1：从 arXiv affiliation 字段匹配
    for author_info in paper.get("affiliations", []):
        for aff in author_info.get("affiliations", []):
            aff_lower = aff.lower()
            for org_name, keywords in KNOWN_ORGS.items():
                for kw in keywords:
                    if kw in aff_lower:
                        identified.add(org_name)
                        break

    # 方式2：从 AI 摘要中提取（DeepSeek 有时能识别出机构）
    ai_org = paper.get("ai_summary", {}).get("org", "")
    if ai_org:
        ai_org_lower = ai_org.lower()
        for org_name, keywords in KNOWN_ORGS.items():
            for kw in keywords:
                if kw in ai_org_lower:
                    identified.add(org_name)
                    break

    # 方式3：从摘要和标题中寻找线索（有些论文会提到公司产品名）
    text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
    product_hints = {
        "OpenAI": ["chatgpt", "gpt-4", "gpt-5", "dall-e", "sora"],
        "Google": ["gemini", "bard", "palm"],
        "Meta": ["llama"],
        "Anthropic": ["claude"],
        "DeepSeek": ["deepseek"],
    }
    for org_name, products in product_hints.items():
        for prod in products:
            if prod in text:
                identified.add(org_name)

    return list(identified)


def analyze_organizations(papers):
    """分析论文的机构分布"""
    org_papers = defaultdict(lambda: {"count": 0, "topics": defaultdict(int), "papers": []})

    for paper in papers:
        orgs = identify_org(paper)
        paper["identified_orgs"] = orgs  # 写回到论文数据中

        for org in orgs:
            org_papers[org]["count"] += 1
            for topic in paper.get("matched_topics", []):
                org_papers[org]["topics"][topic] += 1
            org_papers[org]["papers"].append({
                "title": paper["title"],
                "url": paper.get("url", ""),
                "score": paper.get("ai_summary", {}).get("score", 5),
            })

    # 转换为可序列化的格式，按论文数量排序
    result = []
    for org_name, data in sorted(org_papers.items(), key=lambda x: x[1]["count"], reverse=True):
        result.append({
            "org": org_name,
            "count": data["count"],
            "topics": dict(data["topics"]),
            "papers": data["papers"],
        })

    return result


def main():
    """主流程"""
    print("=" * 60)
    print(f"arXiv 每日论文追踪 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 1. 抓取论文
    papers = fetch_arxiv_papers(days_back=2)
    if not papers:
        print("[结束] 未获取到论文，退出")
        return

    # 2. 关键词匹配 + 排序
    filtered = filter_and_rank(papers)
    if not filtered:
        print("[结束] 没有匹配到相关论文")
        return

    # 3. AI 生成摘要
    print(f"\n[摘要] 正在为 {len(filtered)} 篇论文生成 AI 摘要...")
    results = []
    for i, paper in enumerate(filtered):
        print(f"  [{i+1}/{len(filtered)}] {paper['title'][:50]}...")
        summary = generate_summary(paper)
        if summary:
            paper["ai_summary"] = summary
        else:
            paper["ai_summary"] = {
                "problem": "（摘要生成失败，请查看原文）",
                "method": "",
                "result": "",
                "novelty": "",
                "relevance": "",
                "score": 5,
            }
        results.append(paper)
        time.sleep(1)  # 避免 API 限流

    # 4. 按 AI 评分重新排序
    results.sort(key=lambda x: x["ai_summary"].get("score", 5), reverse=True)

    # 5. 机构分析
    org_stats = analyze_organizations(results)
    print(f"\n[机构] 识别到 {len(org_stats)} 个机构的论文分布")

    # 6. 输出 JSON
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    output = {
        "date": today,
        "generated_at": datetime.now().isoformat(),
        "total_fetched": len(papers),
        "total_matched": len(results),
        "papers": results,
        "org_analysis": org_stats,
    }

    # 写入当天数据
    output_file = output_dir / f"{today}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 同时写入 latest.json 供网页读取
    latest_file = output_dir / "latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 已保存 {len(results)} 篇论文摘要到 {output_file}")
    print(f"[完成] 最新数据已更新到 {latest_file}")


if __name__ == "__main__":
    main()
