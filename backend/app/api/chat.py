from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel, field_validator

from app.core.config import settings
from app.services import conversation_store, session_store, space_store
from app.services.query_planner import plan_query
from app.services.rag import retrieve, retrieve_from_index
from app.services.session_paths import get_rag_cache_dir

logger = logging.getLogger(__name__)
router = APIRouter()

_CACHE_TTL_SECONDS = 300
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    space_id: Optional[str] = None
    conversation_id: Optional[str] = None
    user_id: Optional[str] = "anonymous"
    question: str

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be empty")
        return value.strip()


class Source(BaseModel):
    text: str
    file: str
    page: Optional[int] = None
    doc_id: Optional[str] = None
    doc_order: Optional[int] = None
    source_file_name: Optional[str] = None
    quote: Optional[str] = None
    chunk_id: Optional[int] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    conversation_id: Optional[str] = None
    conversation_title: Optional[str] = None


_SYSTEM_PROMPT = """你是一个文献阅读助手。基于"片段X"提供的论文原文回答用户问题。

输出要求（严格遵守）：
1. 用自然连贯的中文段落回答，必要时再分点
2. 凡是有依据的关键结论 / 数据 / 方法描述，必须在句末紧跟 (第N页) 引用，N 是片段对应的页码数字
3. 同一句可以引用多页：(第3页)(第6页)
4. 信息不足时回答"提供的片段未涉及此内容"，绝不杜撰
5. 不要复述本论文引用的其他文献，不要泛泛地说"论文中提到"

最后必须在答案末尾追加一段 JSON，用 <CITATIONS> 标签包裹，内容是引用映射数组，结构：
<CITATIONS>
[
  {"page": 3, "quote": "论文原文里的一句完整短句，必须逐字复制，不要意译、不要删字、不要加标点", "chunk_id": 2}
]
</CITATIONS>

- quote 用于前端在原 PDF 里做 phrase search 高亮，**必须是原文一字不差的一段连续文字**
- 长度建议 8-25 字 / 6-15 个英文单词。**短优先**：宁可只高亮句首一个明显短语，也不要写一整句因为标点不同导致只高亮一半
- 不要包含 em dash（—）、中文破折号、省略号、引号、括号等特殊字符；如果原文里这些字符正好在你想引的句子中间，请把 quote 截到这些字符**之前**
- 不要跨行；不要包含数学公式
- chunk_id 指向你引用的"片段X"中的 X
- 如果某条 (第N页) 引用找不到合适的短句，可以省略对应 JSON 条目，但答案里的页码必须真实来自片段
- JSON 之外不要再写其他内容，<CITATIONS> 必须出现在回答最末尾
"""


def _cache_key(session_id: str, question: str) -> str:
    payload = f"{session_id}::{question}::{settings.LLM_MODEL}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> dict[str, Any] | None:
    item = _CACHE.get(key)
    if not item:
        return None
    ts, value = item
    if time.time() - ts > _CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: dict[str, Any]) -> None:
    _CACHE[key] = (time.time(), value)


_CITATION_BLOCK_REGEX = re.compile(r"<CITATIONS>\s*(\[.*?\])\s*</CITATIONS>", re.DOTALL | re.IGNORECASE)


def _strip_citation_block(answer: str) -> tuple[str, list[dict[str, Any]]]:
    """从回答尾部抽出 <CITATIONS>...</CITATIONS> JSON，返回净化后的答案和 citations 列表。"""
    match = _CITATION_BLOCK_REGEX.search(answer)
    if not match:
        return answer.strip(), []

    raw_json = match.group(1).strip()
    try:
        citations = json.loads(raw_json)
        if not isinstance(citations, list):
            citations = []
    except json.JSONDecodeError:
        logger.warning("Failed to parse <CITATIONS> JSON: %s", raw_json[:200])
        citations = []

    cleaned_answer = (answer[: match.start()] + answer[match.end() :]).strip()
    return cleaned_answer, citations


_INVISIBLE_REGEX = re.compile(r"[­​‌‍﻿]")  # 软连字符、零宽空格
_LIGATURE_MAP = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"}
_PROBLEMATIC_REGEX = re.compile(r"[–—―…‘’“”]|--")
# 上面包含：– — ― … ' ' " "  以及 ASCII --


def _normalize_quote(text: str) -> str:
    """规范化 quote：折空格 + 删不可见字符 + ligature 还原；遇到容易和 PDF 不一致的字符就截断。

    PDF 抽出的 textLayer 经常和 LLM 写的 quote 在 em dash / 引号 / 连字符上不一致。
    phrase search 是子串精确匹配，差一个字符就只高亮前半段。
    所以策略是：1) 先去掉 PDF 不会有的不可见字符与 ligature；
    2) 检测到容易跑偏的字符（em dash 等），把 quote 截到它之前，宁可短不要错。
    """
    text = (text or "").strip()
    if not text:
        return ""
    text = _INVISIBLE_REGEX.sub("", text)
    for k, v in _LIGATURE_MAP.items():
        text = text.replace(k, v)
    text = re.sub(r"\s+", " ", text).strip()

    cut_match = _PROBLEMATIC_REGEX.search(text)
    if cut_match and cut_match.start() >= 8:
        text = text[: cut_match.start()].rstrip(" ,;:")
    return text[:200]


def _attach_quote_to_sources(
    answer: str,
    citations: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    按 LLM 给出的 citations（quote+page+chunk_id），把 quote 绑到对应 source 上。
    优先用 chunk_id 精确匹配，其次按 page 匹配；多匹配时拷贝多份。
    """
    pages_in_answer = list(dict.fromkeys(
        int(m) for m in re.findall(r"第\s*(\d{1,3})\s*页", answer)
    ))

    by_chunk_id = {s.get("chunk_id"): s for s in sources if s.get("chunk_id")}
    by_page: dict[int, list[dict[str, Any]]] = {}
    for s in sources:
        page = s.get("page")
        if isinstance(page, int):
            by_page.setdefault(page, []).append(s)

    result: list[dict[str, Any]] = []
    full_keys: set[tuple[Any, Optional[int], str]] = set()
    covered_pages: set[int] = set()

    def push(source: dict[str, Any], quote: str | None) -> None:
        normalized_quote = _normalize_quote(quote) if quote else None
        key = (source.get("doc_id"), source.get("page"), normalized_quote or "")
        if key in full_keys:
            return
        full_keys.add(key)
        page_val = source.get("page")
        if isinstance(page_val, int):
            covered_pages.add(page_val)
        copy = dict(source)
        if normalized_quote:
            copy["quote"] = normalized_quote
        result.append(copy)

    for citation in citations:
        if not isinstance(citation, dict):
            continue
        chunk_id = citation.get("chunk_id")
        page = citation.get("page")
        quote = citation.get("quote")
        candidate: dict[str, Any] | None = None
        if isinstance(chunk_id, int) and chunk_id in by_chunk_id:
            candidate = by_chunk_id[chunk_id]
        elif isinstance(page, int) and page in by_page:
            candidate = by_page[page][0]
        if candidate is None:
            continue
        push(candidate, quote if isinstance(quote, str) else None)

    # 答案里出现但 citations JSON 没覆盖的页码，补一个无 quote 的回退源（同页若已覆盖则跳过）
    for page in pages_in_answer:
        if page in covered_pages:
            continue
        for src in by_page.get(page, [])[:1]:
            push(src, None)

    return result


_TITLE_PROMPT = (
    "请用 12 个汉字以内的短语，给下面这一轮提问起一个标题，"
    "只输出标题文字本身，不要引号、不要编号、不要解释。\n\n"
    "用户提问：{question}"
)


def _generate_title(question: str) -> str | None:
    """让 LLM 给会话起一个简短标题；失败回退到截断的问题。"""
    try:
        client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "user", "content": _TITLE_PROMPT.format(question=question[:200])},
            ],
            max_tokens=40,
            temperature=0.3,
        )
        title = (resp.choices[0].message.content or "").strip()
        title = re.sub(r"^[\"'《<\[]+|[\"'》>\]]+$", "", title)
        return title[:30] or None
    except Exception as exc:
        logger.warning("title generation failed: %s", exc)
        question = question.strip()
        return question[:18] + ("..." if len(question) > 18 else "")


def _resolve_retrieval(req: ChatRequest) -> tuple[str, str, str | None]:
    """返回 (mode, target, user_id)。mode='session'|'index_dir'，target 是对应的 id 或目录路径。"""
    user_id = (req.user_id or "anonymous").strip() or "anonymous"

    if req.session_id:
        session = session_store.get_session(req.session_id)
        if session is None:
            # 进程重启后内存里没了，但前端可能传了旧 session_id；如果有 space_id 就降级
            if not req.space_id:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            return ("session", req.session_id, user_id)

    if req.space_id:
        # 优先看内存里有没有该 space 的活跃 session（会带 rag_index_path）
        for sid, sess in session_store._sessions.items():  # type: ignore[attr-defined]
            if sess.space_id == req.space_id and sess.rag_index_path:
                return ("session", sid, user_id)

        # 没有就直接按 space 推断 RAG 索引目录（从 space.json 找历史索引路径，或按惯例规则尝试）
        space = space_store.get(req.space_id)
        if not space:
            raise HTTPException(status_code=404, detail="Space not found")

        candidates = _candidate_index_dirs(space)
        for index_dir in candidates:
            if Path(index_dir).exists() and (Path(index_dir) / "docstore.json").exists():
                return ("index_dir", str(index_dir), user_id)

        raise HTTPException(
            status_code=409,
            detail="该空间还没有可用的 RAG 索引，请重新生成或稍候再试",
        )

    raise HTTPException(status_code=400, detail="必须提供 session_id 或 space_id")


def _candidate_index_dirs(space: dict[str, Any]) -> list[Path]:
    """根据 space 元数据推断对应的 RAG 索引目录候选。"""
    candidates: list[Path] = []
    pdf_hash = space.get("pdf_hash") or ""
    session_type = space.get("session_type", "single")

    if session_type == "single" and pdf_hash:
        # build_index 用的 cache_key 是 "<pdf_hash>-v7"（v6/v5 兼容旧索引）
        for version in ("v7", "v6", "v5"):
            candidates.append(get_rag_cache_dir(f"{pdf_hash}-{version}"))
    else:
        # 多文档：cache_key = sha256(pdf_hashes)[:16] + "-multi-v2"
        # 没有 pdf_hash 时遍历 rag_cache_path 看哪个目录新且 docstore 存在
        rag_root = settings.rag_cache_path
        if rag_root.exists():
            for path in sorted(rag_root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if path.is_dir() and (path / "docstore.json").exists():
                    candidates.append(path)
                    if len(candidates) >= 5:
                        break
    return candidates


@router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    mode, target, user_id = _resolve_retrieval(req)
    space_id = req.space_id

    cache_seed = req.conversation_id or req.space_id or req.session_id or ""
    cache_key = _cache_key(cache_seed, req.question)
    cached = _cache_get(cache_key)
    if cached:
        logger.info("Chat cache HIT  key=%s  q=%r", cache_seed, req.question)
        return ChatResponse(**cached)

    # 多文档 space → 先调 planner 决定查询路由
    plan = None
    space_data = space_store.get(space_id) if space_id else None
    if space_data:
        source_documents = space_data.get("source_documents") or []
        if len(source_documents) > 1:
            plan = plan_query(req.question, space_id, source_documents)

    started = time.time()
    if mode == "session":
        session = session_store.get_session(target)
        if session and session.rag_index_path:
            context, sources = retrieve_from_index(session.rag_index_path, req.question, plan=plan)
        else:
            context, sources = retrieve(target, req.question)
    else:
        context, sources = retrieve_from_index(target, req.question, plan=plan)
    retrieval_elapsed = time.time() - started

    user_content = req.question
    if context:
        user_content = (
            f"以下是检索到的论文相关片段：\n\n{context}\n\n"
            f"用户问题：{req.question}\n\n"
            f"请基于这些片段作答，并按系统提示在末尾输出 <CITATIONS> JSON。"
        )

    llm_started = time.time()
    try:
        client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1500,
            temperature=0.2,
        )
        raw_answer = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}") from exc
    llm_elapsed = time.time() - llm_started

    cleaned_answer, citations = _strip_citation_block(raw_answer)
    final_sources = _attach_quote_to_sources(cleaned_answer, citations, sources)
    sources_payload = [Source(**item).model_dump() for item in final_sources]

    new_title: str | None = None
    if space_id and req.conversation_id:
        try:
            existing = conversation_store.get_conversation(user_id, space_id, req.conversation_id)
            is_first_question = not (existing and existing.get("messages"))
            conversation_store.append_message(
                user_id, space_id, req.conversation_id,
                role="user", content=req.question,
            )
            conversation_store.append_message(
                user_id, space_id, req.conversation_id,
                role="assistant", content=cleaned_answer, sources=sources_payload,
            )
            if is_first_question:
                new_title = _generate_title(req.question)
                if new_title:
                    conversation_store.rename(user_id, space_id, req.conversation_id, new_title)
        except KeyError:
            logger.warning("conversation %s not found, message not persisted", req.conversation_id)

    if space_id:
        space_store.touch_access(space_id, user_id)

    logger.info(
        "Chat done  mode=%s  target=%s  space=%s  conv=%s  retrieval=%.2fs  llm=%.2fs  sources=%d  citations=%d",
        mode, target, space_id, req.conversation_id,
        retrieval_elapsed, llm_elapsed, len(final_sources), len(citations),
    )

    payload = {
        "answer": cleaned_answer,
        "sources": sources_payload,
        "conversation_id": req.conversation_id,
        "conversation_title": new_title,
    }
    _cache_set(cache_key, payload)
    return ChatResponse(**payload)
