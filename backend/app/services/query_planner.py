"""Query planner：让一个轻量 LLM 提前看一眼问题，决定 RAG 应该查哪些文档、用什么子查询。

仅在多文档 space 下使用。单文档直接跳过。
输出结构（QueryPlan）：
  scope: "all" | "single"
  doc_id: 仅当 scope=single
  subqueries: scope=all 时每个 doc 的具体查询；scope=single 时该 doc 的具体查询（可选）
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300
_CACHE: dict[str, tuple[float, "QueryPlan"]] = {}


@dataclass
class QueryPlan:
    scope: str = "all"  # "all" | "single"
    doc_id: str | None = None
    subqueries: list[str] = field(default_factory=list)
    raw: str | None = None  # 调试用


_SYSTEM_PROMPT = """你是一个论文检索路由助手。给定用户问题与当前空间下所有论文的元数据，判断这次检索应该覆盖哪些论文、用什么子查询。

只输出 JSON，不要任何解释或 markdown 标记。结构：
{
  "scope": "all" | "single",
  "doc_id": "doc_xxx" 或 null,
  "subqueries": ["...", "..."]
}

判断规则：
- 用户提到"两篇/分别/对比/它们/各自/都/比较"等多篇范围词 → scope="all"，**每篇生成一个不同的子查询**（在子查询里把通用词替换成具体论文名/编号），子查询数量等于论文数量
- 用户明确指出某一篇（论文标题、第一篇/第二篇、Chronos/M+ 这类专有名词）→ scope="single"，doc_id 填那一篇，subqueries 给一个该论文的具体查询
- 用户没指明范围、没提对比/分别 → scope="all"，**subqueries 只给一个原问题**（不要重复），让检索自己去匹配

例子：
问题：两篇论文分别有什么创新点
文档：doc_001=Chronos: Temporal-Aware..., doc_002=Zep: A Temporal Knowledge...
输出：{"scope":"all","doc_id":null,"subqueries":["Chronos 的创新点","Zep 的创新点"]}

问题：Chronos 是怎么处理时间的
文档同上
输出：{"scope":"single","doc_id":"doc_001","subqueries":["Chronos 时间处理方法"]}

问题：实验结果怎么样
文档同上
输出：{"scope":"all","doc_id":null,"subqueries":["实验结果"]}
"""


def _cache_key(space_id: str, question: str) -> str:
    return hashlib.sha256(f"{space_id}::{question}".encode("utf-8")).hexdigest()


def _cache_get(key: str) -> QueryPlan | None:
    item = _CACHE.get(key)
    if not item:
        return None
    ts, value = item
    if time.time() - ts > _CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: QueryPlan) -> None:
    _CACHE[key] = (time.time(), value)


def _build_user_content(question: str, source_documents: list[dict[str, Any]]) -> str:
    docs_lines = []
    for doc in source_documents:
        doc_id = doc.get("doc_id") or ""
        name = doc.get("source_file_name") or doc.get("pdf_path") or "unknown"
        docs_lines.append(f"  {doc_id}: {name}")
    docs_block = "\n".join(docs_lines) or "(无文档元数据)"
    return f"当前空间包含以下论文：\n{docs_block}\n\n用户问题：{question}"


_VALID_SCOPES = {"all", "single"}


def _parse_plan(raw: str, valid_doc_ids: set[str]) -> QueryPlan:
    """JSON 解析容错。"""
    text = raw.strip()
    # 容错：模型偶尔会包 ```json ... ```
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 再次尝试抓第一个 JSON 块
        match = re.search(r"\{[\s\S]+\}", text)
        if not match:
            raise
        data = json.loads(match.group(0))

    scope = data.get("scope", "all")
    if scope not in _VALID_SCOPES:
        scope = "all"

    doc_id = data.get("doc_id")
    if doc_id and doc_id not in valid_doc_ids:
        # LLM 可能编了一个不存在的 doc_id，降级到 all
        logger.warning("planner returned unknown doc_id=%s, downgrading to scope=all", doc_id)
        scope = "all"
        doc_id = None

    subqueries_raw = data.get("subqueries") or []
    if isinstance(subqueries_raw, str):
        subqueries_raw = [subqueries_raw]
    subqueries = [str(q).strip() for q in subqueries_raw if str(q).strip()]
    if not subqueries:
        subqueries = []

    return QueryPlan(scope=scope, doc_id=doc_id if scope == "single" else None, subqueries=subqueries, raw=raw)


def plan_query(
    question: str,
    space_id: str,
    source_documents: list[dict[str, Any]],
) -> QueryPlan:
    """对多文档 space 做查询规划。失败时返回 fallback plan（scope=all, subqueries=[question]）。"""
    fallback = QueryPlan(scope="all", subqueries=[question])
    if not source_documents or len(source_documents) <= 1:
        return fallback

    cache_key = _cache_key(space_id, question)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    valid_doc_ids = {str(d.get("doc_id")) for d in source_documents if d.get("doc_id")}

    try:
        client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        started = time.time()
        resp = client.chat.completions.create(
            model=settings.LLM_PLANNER_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_content(question, source_documents)},
            ],
            max_tokens=300,
            temperature=0.0,
        )
        raw = (resp.choices[0].message.content or "").strip()
        elapsed = time.time() - started
        plan = _parse_plan(raw, valid_doc_ids)
        if not plan.subqueries:
            plan.subqueries = [question]
        logger.info(
            "[planner] %.2fs scope=%s doc=%s subqueries=%s",
            elapsed, plan.scope, plan.doc_id, plan.subqueries,
        )
    except Exception as exc:
        logger.warning("[planner] failed, falling back to scope=all: %s", exc)
        plan = fallback

    _cache_set(cache_key, plan)
    return plan
