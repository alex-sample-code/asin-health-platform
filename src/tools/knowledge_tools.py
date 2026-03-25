"""知识库检索工具 — 从 data/knowledge_docs/ 读取 Markdown 文档，简单关键词匹配。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from strands import tool

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
KNOWLEDGE_DIR = DATA_DIR / "knowledge_docs"

# 缓存：文件名 → 内容
_docs_cache: dict[str, str] | None = None


def _load_docs() -> dict[str, str]:
    """加载所有知识库文档。"""
    global _docs_cache
    if _docs_cache is not None:
        return _docs_cache

    _docs_cache = {}
    if not KNOWLEDGE_DIR.exists():
        return _docs_cache

    for fp in KNOWLEDGE_DIR.glob("*.md"):
        with open(fp, "r", encoding="utf-8") as f:
            _docs_cache[fp.stem] = f.read()
    return _docs_cache


def _extract_relevant_sections(content: str, keywords: list[str], context_lines: int = 5) -> list[str]:
    """从文档中提取包含关键词的段落。"""
    lines = content.split("\n")
    matched_sections: list[str] = []
    current_section: list[str] = []
    section_has_match = False

    for line in lines:
        # 新章节开始
        if line.startswith("## ") or line.startswith("# "):
            if section_has_match and current_section:
                matched_sections.append("\n".join(current_section))
            current_section = [line]
            section_has_match = False
        else:
            current_section.append(line)

        # 检查关键词匹配
        line_lower = line.lower()
        for kw in keywords:
            if kw.lower() in line_lower:
                section_has_match = True
                break

    # 处理最后一个段落
    if section_has_match and current_section:
        matched_sections.append("\n".join(current_section))

    return matched_sections


@tool
def search_knowledge(query: str) -> str:
    """在运营知识库中搜索与查询相关的文档内容。

    支持中英文关键词搜索，返回匹配的文档段落。
    知识库包含：季节性规律、常见异常模式、库存管理SOP、广告优化SOP、Listing优化SOP、退货处理SOP、Amazon政策更新。

    Args:
        query: 搜索关键词或问题，如 "退货率高怎么办"、"广告ACOS优化"、"季节性"
    """
    docs = _load_docs()
    if not docs:
        return json.dumps({"error": "知识库为空"}, ensure_ascii=False)

    # 分词：中文连续字符作为整体 + 按 2 字滑动窗口拆分，英文按空格
    raw_tokens = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", query.lower())
    keywords: list[str] = []
    for token in raw_tokens:
        keywords.append(token)
        # 中文长词额外拆成 2-gram
        if len(token) >= 2 and re.match(r"[\u4e00-\u9fff]", token):
            for i in range(len(token) - 1):
                bigram = token[i : i + 2]
                if bigram not in keywords:
                    keywords.append(bigram)
    if not keywords:
        return json.dumps({"error": "无有效关键词"}, ensure_ascii=False)

    results: list[dict[str, Any]] = []
    for doc_name, content in docs.items():
        # 文档名匹配得分
        name_score = sum(1 for kw in keywords if kw in doc_name.lower())
        # 内容匹配
        sections = _extract_relevant_sections(content, keywords)
        if sections or name_score > 0:
            # 计算总匹配度
            content_lower = content.lower()
            content_score = sum(content_lower.count(kw) for kw in keywords)
            total_score = name_score * 10 + content_score

            results.append({
                "document": doc_name,
                "relevance_score": total_score,
                "matched_sections": sections[:3],  # 最多 3 个段落
            })

    # 按相关度排序
    results.sort(key=lambda x: x["relevance_score"], reverse=True)

    output = {
        "query": query,
        "keywords": keywords,
        "total_docs_searched": len(docs),
        "results": results[:5],  # 最多返回 5 个文档
    }
    return json.dumps(output, ensure_ascii=False, indent=2)
