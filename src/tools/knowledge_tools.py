"""知识库检索工具 — 从 S3 读取 Markdown 文档，简单关键词匹配。"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import boto3
from strands import tool

S3_BUCKET = os.environ.get("S3_BUCKET", "asin-health-platform-data-959545103699")
REGION = os.environ.get("AWS_REGION", "us-east-1")

_s3 = None
_docs_cache: dict[str, str] | None = None


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=REGION)
    return _s3


def _load_docs() -> dict[str, str]:
    """从 S3 加载所有知识库文档。"""
    global _docs_cache
    if _docs_cache is not None:
        return _docs_cache

    s3 = _get_s3()
    _docs_cache = {}
    resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix="knowledge_docs/")
    for obj in resp.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".md"):
            body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read().decode("utf-8")
            doc_name = key.split("/")[-1].replace(".md", "")
            _docs_cache[doc_name] = body
    return _docs_cache


def _extract_relevant_sections(content: str, keywords: list[str]) -> list[str]:
    """从文档中提取包含关键词的段落。"""
    lines = content.split("\n")
    matched_sections: list[str] = []
    current_section: list[str] = []
    section_has_match = False

    for line in lines:
        if line.startswith("## ") or line.startswith("# "):
            if section_has_match and current_section:
                matched_sections.append("\n".join(current_section))
            current_section = [line]
            section_has_match = False
        else:
            current_section.append(line)

        line_lower = line.lower()
        for kw in keywords:
            if kw.lower() in line_lower:
                section_has_match = True
                break

    if section_has_match and current_section:
        matched_sections.append("\n".join(current_section))

    return matched_sections


@tool
def search_knowledge(query: str) -> str:
    """在运营知识库中搜索与查询相关的文档内容。

    Args:
        query: 搜索关键词或问题，如 "退货率高怎么办"、"广告ACOS优化"
    """
    docs = _load_docs()
    if not docs:
        return json.dumps({"error": "知识库为空"}, ensure_ascii=False)

    raw_tokens = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", query.lower())
    keywords: list[str] = []
    for token in raw_tokens:
        keywords.append(token)
        if len(token) >= 2 and re.match(r"[\u4e00-\u9fff]", token):
            for i in range(len(token) - 1):
                bigram = token[i : i + 2]
                if bigram not in keywords:
                    keywords.append(bigram)
    if not keywords:
        return json.dumps({"error": "无有效关键词"}, ensure_ascii=False)

    results: list[dict[str, Any]] = []
    for doc_name, content in docs.items():
        name_score = sum(1 for kw in keywords if kw in doc_name.lower())
        sections = _extract_relevant_sections(content, keywords)
        if sections or name_score > 0:
            content_lower = content.lower()
            content_score = sum(content_lower.count(kw) for kw in keywords)
            total_score = name_score * 10 + content_score
            results.append({
                "document": doc_name,
                "relevance_score": total_score,
                "matched_sections": sections[:3],
            })

    results.sort(key=lambda x: x["relevance_score"], reverse=True)

    output = {
        "query": query,
        "total_docs_searched": len(docs),
        "results": results[:3],
    }
    return json.dumps(output, ensure_ascii=False, indent=2)
