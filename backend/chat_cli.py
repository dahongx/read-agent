"""终端交互式 RAG 问答测试工具

用法（在 backend/ 目录下，激活 venv 后）：

    # 用某个 PDF 跑（自动建索引到 backend/uploads/cache/rag/<sha>-cli/）
    python chat_cli.py --pdf path/to/paper.pdf

    # 复用已有索引目录（必须含 docstore.json + bm25_corpus.json）
    python chat_cli.py --index backend/uploads/cache/rag/<some-dir>

    # 单条问题（非交互）
    python chat_cli.py --pdf paper.pdf --question "How does M+ extend MemoryLLM?"

每问一句，输出：
    1) Claude 的中文回答（已剥离 <CITATIONS> JSON）
    2) 每条 (第N页) 引用对应的 verbatim quote、page、命中片段预览
    3) 检索/LLM 各自耗时
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# 让脚本既能在 backend/ 目录运行，也能在仓库根目录运行
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Windows 控制台默认 GBK，强制 stdout/stderr 用 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from openai import OpenAI

from app.api.chat import (
    _SYSTEM_PROMPT,
    _attach_quote_to_sources,
    _strip_citation_block,
)
from app.core.config import settings
from app.services.rag import _build_context_and_sources
from app.services.rag_index import _BM25_CORPUS_FILENAME, build_index, query_index
from app.services.reranker import rerank


# 颜色：默认开启；非 TTY、Windows cmd（无 ANSICON）或 NO_COLOR 时自动关闭
def _color_supported() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    if sys.platform == "win32":
        # 现代 Windows Terminal / VSCode 都支持，传统 cmd 不支持
        return bool(os.environ.get("WT_SESSION") or os.environ.get("ANSICON"))
    return True


_USE_COLOR = _color_supported()
COLOR_RESET = "\033[0m" if _USE_COLOR else ""
COLOR_BOLD = "\033[1m" if _USE_COLOR else ""
COLOR_DIM = "\033[2m" if _USE_COLOR else ""
COLOR_CYAN = "\033[36m" if _USE_COLOR else ""
COLOR_GREEN = "\033[32m" if _USE_COLOR else ""
COLOR_YELLOW = "\033[33m" if _USE_COLOR else ""
COLOR_RED = "\033[31m" if _USE_COLOR else ""
COLOR_MAGENTA = "\033[35m" if _USE_COLOR else ""

HIT_OK = "[HIT]"
HIT_MISS = "[MISS]"


def _cprint(text: str, color: str = "") -> None:
    print(f"{color}{text}{COLOR_RESET}" if color else text)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _resolve_index_dir(pdf_path: Path | None, index_dir: Path | None) -> Path:
    if index_dir:
        if not index_dir.is_dir():
            raise SystemExit(f"index dir does not exist: {index_dir}")
        return index_dir

    assert pdf_path is not None
    pdf_hash = _hash_file(pdf_path)
    target = settings.rag_cache_path / f"{pdf_hash}-cli"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _ensure_index(pdf_path: Path | None, index_dir: Path) -> None:
    docstore = index_dir / "docstore.json"
    bm25 = index_dir / _BM25_CORPUS_FILENAME

    if docstore.exists() and bm25.exists():
        _cprint(f"[index] reuse {index_dir} (bm25 ready)", COLOR_DIM)
        return

    if not pdf_path:
        raise SystemExit(
            f"index dir incomplete (docstore={docstore.exists()}, bm25={bm25.exists()})\n"
            f"请用 --pdf 重新构建带 BM25 的索引"
        )

    _cprint(f"[index] building from {pdf_path}", COLOR_CYAN)
    started = time.time()
    build_index(str(pdf_path), str(index_dir))
    _cprint(f"[index] done in {time.time() - started:.1f}s", COLOR_DIM)


def _ask_once(question: str, index_dir: Path, *, llm_client: OpenAI) -> None:
    print()
    _cprint("=" * 72, COLOR_DIM)
    _cprint(f"Q: {question}", COLOR_BOLD)
    _cprint("=" * 72, COLOR_DIM)

    t_retrieve = time.time()
    candidates = query_index(str(index_dir), question)
    if not candidates:
        _cprint("[retrieve] no candidates returned", COLOR_RED)
        return
    top = rerank(question, candidates)
    if not top:
        _cprint("[rerank] dropped all candidates", COLOR_RED)
        return
    context, sources = _build_context_and_sources(top)
    retrieve_elapsed = time.time() - t_retrieve

    _cprint(
        f"[retrieve] {retrieve_elapsed:.2f}s  candidates={len(candidates)}  "
        f"after_rerank={len(top)}  context_chars={len(context)}",
        COLOR_DIM,
    )

    user_content = (
        f"以下是检索到的论文相关片段：\n\n{context}\n\n"
        f"用户问题：{question}\n\n"
        f"请基于这些片段作答，并按系统提示在末尾输出 <CITATIONS> JSON。"
    )

    t_llm = time.time()
    try:
        response = llm_client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1500,
            temperature=0.2,
        )
    except Exception as exc:
        _cprint(f"[llm] failed: {exc}", COLOR_RED)
        return
    raw_answer = (response.choices[0].message.content or "").strip()
    llm_elapsed = time.time() - t_llm

    cleaned, citations = _strip_citation_block(raw_answer)
    final_sources = _attach_quote_to_sources(cleaned, citations, sources)

    print()
    _cprint("─── ANSWER ─" + "─" * 60, COLOR_GREEN)
    print(cleaned if cleaned else "(empty)")
    print()

    if citations:
        _cprint(f"─── CITATIONS ({len(citations)}) ─" + "─" * 50, COLOR_YELLOW)
        for idx, cit in enumerate(citations, 1):
            if not isinstance(cit, dict):
                continue
            page = cit.get("page", "?")
            chunk_id = cit.get("chunk_id", "?")
            quote = cit.get("quote") or ""
            _cprint(f"[{idx}] page={page}  chunk={chunk_id}", COLOR_YELLOW)
            print(f"    {COLOR_MAGENTA}quote{COLOR_RESET}: {quote}")
            chunk = next((s for s in sources if s.get("chunk_id") == chunk_id), None)
            if chunk:
                quote_norm = re.sub(r"\s+", " ", quote.strip())
                full_norm = re.sub(r"\s+", " ", chunk.get("full_text") or "")
                hit = bool(quote_norm) and quote_norm in full_norm
                hit_label = HIT_OK if hit else HIT_MISS
                color = COLOR_GREEN if hit else COLOR_RED
                _cprint(f"    verbatim_in_chunk: {hit_label}", color)
        print()
    else:
        _cprint("(no <CITATIONS> JSON returned by LLM)", COLOR_RED)

    _cprint(
        f"─── SOURCES (final, {len(final_sources)}) ─" + "─" * 40,
        COLOR_CYAN,
    )
    for idx, src in enumerate(final_sources, 1):
        flags = []
        if src.get("quote"):
            flags.append("quote")
        if src.get("doc_id"):
            flags.append(f"doc={src['doc_id']}")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        _cprint(
            f"  {idx:>2}. page={src.get('page')}  chunk={src.get('chunk_id')}{flag_str}",
            COLOR_CYAN,
        )

    _cprint(
        f"\n[timing] retrieve={retrieve_elapsed:.2f}s  llm={llm_elapsed:.2f}s  "
        f"total={retrieve_elapsed + llm_elapsed:.2f}s",
        COLOR_DIM,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="终端交互式 RAG 问答测试")
    parser.add_argument("--pdf", type=Path, help="PDF 路径（首次会建索引到 cache/rag/<sha>-cli/）")
    parser.add_argument("--index", type=Path, help="直接使用某个已有索引目录")
    parser.add_argument("--question", "-q", help="单次问题（非交互模式）")
    parser.add_argument("--quiet", action="store_true", help="抑制后端 INFO 日志")
    args = parser.parse_args()

    if not args.pdf and not args.index:
        parser.error("必须指定 --pdf 或 --index 至少一个")

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    pdf_path = args.pdf.resolve() if args.pdf else None
    if pdf_path and not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    index_dir = _resolve_index_dir(pdf_path, args.index.resolve() if args.index else None)
    _ensure_index(pdf_path, index_dir)

    if not settings.LLM_API_KEY:
        raise SystemExit("LLM_API_KEY not set in backend/.env")

    _cprint(f"[llm] {settings.LLM_BASE_URL}  model={settings.LLM_MODEL}", COLOR_DIM)
    _cprint(
        f"[rag] reranker_enabled={settings.RERANKER_ENABLED}  "
        f"top_k_dense={settings.RAG_TOP_K_DENSE}  bm25={settings.RAG_TOP_K_BM25}  "
        f"final={settings.RAG_TOP_K_FINAL}",
        COLOR_DIM,
    )

    llm_client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

    if args.question:
        _ask_once(args.question, index_dir, llm_client=llm_client)
        return

    _cprint("\n输入问题（空行 / Ctrl+C 退出）", COLOR_BOLD)
    while True:
        try:
            question = input(f"\n{COLOR_BOLD}>>>{COLOR_RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            break
        try:
            _ask_once(question, index_dir, llm_client=llm_client)
        except KeyboardInterrupt:
            _cprint("\n[interrupted, ask another or empty to exit]", COLOR_RED)


if __name__ == "__main__":
    main()
