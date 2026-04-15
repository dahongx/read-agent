from __future__ import annotations

import logging
import re
from typing import Optional

from openai import OpenAI
from fastapi import APIRouter, HTTPException
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
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty")
        return v.strip()


class Source(BaseModel):
    text: str
    file: str
    page: Optional[int] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


_SYSTEM_PROMPT = """你是一个文献阅读助手，基于提供的论文原文片段回答问题。

【强制要求】每个分论点结尾必须附上页码标注，格式为半角括号加中文，例如 (第3页)。
示例：M+通过长期记忆池扩展了短期记忆容量(第2页)。实验表明该方法在LongBench上领先基线(第6页)。

规则：
- 只用提供的片段，禁止添加片段中未出现的信息
- 每个论点必须有 (第N页) 标注，N是该片段对应的页码数字
- 提供的片段不足时说"提供的片段未涉及此内容"，不要推断
- 不要提及本论文引用的其他文献
- 用中文回答"""


def _parse_citations(answer: str, retrieved: list[dict]) -> list[dict]:
    """从 LLM 答案中解析 (第N页) 标注，返回实际引用的 source 列表（保序去重）。"""
    pages = list(dict.fromkeys(int(m) for m in re.findall(r'第(\d{1,3})页', answer)))
    result = []
    for page in pages:
        chunk = next((s for s in retrieved if s.get("page") == page), None)
        if chunk:
            result.append(chunk)
        # Skip pages the LLM hallucinated (not in retrieved set)
    return result


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
        answer = response.choices[0].message.content or ""
    except Exception as exc:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    # Use LLM-cited pages as sources (much more accurate than all top-k chunks)
    cited = _parse_citations(answer, sources)
    final_sources = cited if cited else sources  # fallback to retrieved if LLM cited nothing

    return ChatResponse(
        answer=answer,
        sources=[Source(**s) for s in final_sources],
    )
