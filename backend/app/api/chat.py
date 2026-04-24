from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel, field_validator

from app.core.config import settings
from app.services import session_store
from app.services.rag import retrieve

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
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


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


_SYSTEM_PROMPT = """你是一个文献阅读助手，基于提供的论文原文片段回答问题。

请用自然、正常的中文直接回答，默认写成连贯段落；只有在用户明确要求时才分点或编号。
凡是有明确依据的句子，请在句末附上页码标注，格式为半角括号加中文，例如 (第3页)。
示例：M+ 通过长期记忆池扩展了短期记忆容量(第2页)。实验表明该方法在 LongBench 上领先基线(第6页)。

规则：
- 只用提供的片段，禁止添加片段中未出现的信息
- 有依据的关键结论或事实句必须有 (第N页) 标注，N 是该片段对应的页码数字
- 不要为了凑格式强行分点、编号或写得很生硬
- 提供的片段不足时说“提供的片段未涉及此内容”，不要推断
- 不要提及本论文引用的其他文献
- 用中文回答
"""


def _parse_citations(answer: str, retrieved: list[dict]) -> list[dict]:
    """Extract cited pages from the answer and map them back to retrieved chunks."""
    pages = list(
        dict.fromkeys(
            int(match) for match in re.findall(r"第\s*(\d{1,3})\s*页", answer)
        )
    )
    results: list[dict] = []

    for page in pages:
        chunk = next((item for item in retrieved if item.get("page") == page), None)
        if chunk is not None:
            results.append(chunk)

    return results


@router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    session = session_store.get_session(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    context, sources = retrieve(req.session_id, req.question)

    user_content = req.question
    if context:
        user_content = f"以下是论文相关内容片段：\n\n{context}\n\n用户问题：{req.question}"

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
            max_tokens=1024,
        )
        answer = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}") from exc

    cited_sources = _parse_citations(answer, sources)
    final_sources = cited_sources if cited_sources else sources

    return ChatResponse(
        answer=answer,
        sources=[Source(**item) for item in final_sources],
    )
