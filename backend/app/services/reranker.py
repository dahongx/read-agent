from __future__ import annotations

import logging
import time
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_RERANKER_CACHE: Any = None


def _get_reranker():
    global _RERANKER_CACHE
    if _RERANKER_CACHE is not None:
        return _RERANKER_CACHE

    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        logger.warning("sentence_transformers not installed; reranker disabled")
        return None

    settings.embed_cache_path.mkdir(parents=True, exist_ok=True)
    try:
        _RERANKER_CACHE = CrossEncoder(
            settings.RERANKER_MODEL_NAME,
            cache_folder=str(settings.embed_cache_path),
            trust_remote_code=True,
        )
        logger.info("Reranker loaded: %s", settings.RERANKER_MODEL_NAME)
    except Exception as exc:
        logger.exception("Failed to load reranker: %s", exc)
        _RERANKER_CACHE = None
    return _RERANKER_CACHE


def rerank(
    question: str,
    candidates: list[dict[str, Any]],
    *,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """对候选 chunk 做 cross-encoder 重排。失败/未启用时按原顺序截断。"""
    if not candidates:
        return []

    top_k = top_k or settings.RAG_TOP_K_FINAL

    if not settings.RERANKER_ENABLED:
        return candidates[:top_k]

    model = _get_reranker()
    if model is None:
        return candidates[:top_k]

    started = time.time()
    pairs = [(question, chunk.get("full_text") or chunk.get("text") or "") for chunk in candidates]
    try:
        scores = model.predict(pairs, show_progress_bar=False)
    except Exception as exc:
        logger.exception("Reranker.predict failed; fallback to original order: %s", exc)
        return candidates[:top_k]

    ranked = sorted(
        ((float(score), idx) for idx, score in enumerate(scores)),
        key=lambda item: item[0],
        reverse=True,
    )
    result: list[dict[str, Any]] = []
    for score, idx in ranked[:top_k]:
        chunk = dict(candidates[idx])
        chunk["rerank_score"] = score
        result.append(chunk)

    logger.info(
        "Rerank %.2fs  candidates=%d  -> top_%d  best_score=%.3f",
        time.time() - started,
        len(candidates),
        len(result),
        result[0]["rerank_score"] if result else 0.0,
    )
    return result
