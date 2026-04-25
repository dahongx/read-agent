from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import subprocess as _sp
import sys
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.models import PptConfig, SessionSourceDoc
from app.services import session_store

logger = logging.getLogger(__name__)

CLAUDE_CLI = settings.claude_cli_path
GIT_BASH = settings.git_bash_path
PYTHON = sys.executable
REPO_ROOT = str(settings.project_root)
SKILL_NAME = settings.skill_path.name
CACHE_MANIFEST_NAME = "project_manifest.json"
CLAUDE_IDLE_WARN_SECONDS = 60

logger.info("[ppt_generator] REPO_ROOT resolved to: %s", REPO_ROOT)
logger.info(
    "[ppt_generator] CLAUDE_CLI: %s  exists=%s",
    CLAUDE_CLI,
    CLAUDE_CLI.exists() if CLAUDE_CLI else False,
)


class GenerationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        source: str = "ppt",
        stage: str = "",
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        super().__init__(message)
        self.source = source
        self.stage = stage
        self.stdout_tail = stdout[-10000:] if stdout else None
        self.stderr_tail = stderr[-10000:] if stderr else None


def compute_cache_key(pdf_path: str, config: PptConfig) -> str:
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    pdf_hash = h.hexdigest()[:16]
    config_hash = hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:8]
    return f"{pdf_hash}-{config_hash}"


def _hash_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_multi_cache_key(pdf_paths: list[str], config: PptConfig, *, merge_version: str = "multi-v1") -> str:
    h = hashlib.sha256()
    for idx, pdf_path in enumerate(pdf_paths, start=1):
        h.update(f"{idx}:".encode("utf-8"))
        h.update(_hash_file(pdf_path).encode("utf-8"))
    config_hash = hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:8]
    merge_hash = hashlib.sha256(merge_version.encode("utf-8")).hexdigest()[:8]
    return f"{h.hexdigest()[:16]}-{config_hash}-{merge_hash}"


def run_skill_script(script_name: str, *args: str, allow_partial_failure: bool = False) -> str:
    script_path = settings.skill_path / "scripts" / script_name
    cmd = [PYTHON, str(script_path)] + list(args)
    logger.info("Running: %s", " ".join(cmd))
    result = _sp.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if result.returncode != 0 and not allow_partial_failure:
        raise RuntimeError(f"{script_name} failed (exit {result.returncode}):\n{stderr[-2000:]}")
    if result.returncode != 0:
        logger.warning("%s exited with %d:\n%s", script_name, result.returncode, stderr[-500:])
    return stdout


def _build_batch_prompt(pdf_path: str, config: PptConfig) -> str:
    return (
        f"[BATCH_MODE]\n"
        f"/{SKILL_NAME}\n\n"
        f"请只使用 /{SKILL_NAME} 完成这次任务，不要调用其他 skill。\n"
        f"这是后端批处理任务，不是交互式对话。请严格按批量模式执行：\n"
        f"- 跳过模板选择与八项确认的阻塞等待，不要调用 AskUserQuestion\n"
        f"- 直接使用下列已确认参数；未显式提供的确认项按默认学术汇报规则补全\n"
        f"- 若模板为自由设计，则不要查询模板选项，直接继续\n"
        f"- 连续执行到 svg_final 和 pptx 导出后再结束\n\n"
        f"运行环境补充约束：\n"
        f"- 当前是 Windows 后端任务，请不要假设 `python3` 命令存在\n"
        f"- 如需运行 Python 脚本，请优先使用这个解释器：{PYTHON}\n"
        f"- 如需调用 skill 内脚本，请使用绝对路径，并优先写成：\"{PYTHON}\" \"<script_path>\"\n\n"
        f"论文PDF：{pdf_path}\n"
        f"模板：{config.template_prompt_value}\n"
        f"语言：{config.language}\n"
        f"受众：{config.audience}\n\n"
        f"八项确认：\n"
        f"1. Canvas格式：ppt169\n"
        f"2. 页数：{config.page_count}页\n"
        f"3. 目标受众：{config.audience}\n"
        f"4. 风格：{config.style}\n"
        f"5. 配色：{config.color_scheme_prompt_value}\n"
        f"6. 图标：适量线条图标\n"
        f"7. 字体：标题大字加粗，正文14-16pt\n"
        f"8. 图片：不生成AI图片，使用文字+图表+数据可视化\n\n"
        f"Speaker notes：每页100-200字口语化中文，讲论文内容，不要讲排版规范\n\n"
        f"以上配置已由用户在 Web 前端收集并确认，其余确认项已由系统按默认规则解析。"
        f"请直接完成到 svg_final 和 pptx 导出，不要调用 AskUserQuestion，也不要再询问任何问题。"
    )


def _build_multi_batch_prompt(merged_md_path: str, config: PptConfig) -> str:
    return (
        f"[BATCH_MODE]\n"
        f"/{SKILL_NAME}\n\n"
        f"请只使用 /{SKILL_NAME} 完成这次任务，不要调用其他 skill。\n"
        f"这是后端批处理任务，不是交互式对话。请严格按批量模式执行：\n"
        f"- 跳过模板选择与八项确认的阻塞等待，不要调用 AskUserQuestion\n"
        f"- 直接使用下列已确认参数；未显式提供的确认项按默认学术汇报规则补全\n"
        f"- 若模板为自由设计，则不要查询模板选项，直接继续\n"
        f"- 连续执行到 svg_final 和 pptx 导出后再结束\n"
        f"- 本次任务是多篇论文综述汇报，不是单篇论文复述\n\n"
        f"运行环境补充约束：\n"
        f"- 当前是 Windows 后端任务，请不要假设 `python3` 命令存在\n"
        f"- 如需运行 Python 脚本，请优先使用这个解释器：{PYTHON}\n"
        f"- 如需调用 skill 内脚本，请使用绝对路径，并优先写成：\"{PYTHON}\" \"<script_path>\"\n\n"
        f"主资料 Markdown：{merged_md_path}\n"
        f"模板：{config.template_prompt_value}\n"
        f"语言：{config.language}\n"
        f"受众：{config.audience}\n\n"
        f"八项确认：\n"
        f"1. Canvas格式：ppt169\n"
        f"2. 页数：{config.page_count}页\n"
        f"3. 目标受众：{config.audience}\n"
        f"4. 风格：{config.style}\n"
        f"5. 配色：{config.color_scheme_prompt_value}\n"
        f"6. 图标：适量线条图标\n"
        f"7. 字体：标题大字加粗，正文14-16pt\n"
        f"8. 图片：不生成AI图片，优先复用源资料中的图表、插图与数据可视化\n\n"
        f"内容要求：\n"
        f"- 以多篇论文综述/Survey 汇报方式组织内容\n"
        f"- 重点围绕研究背景、问题定义、方法脉络、核心结果、局限性、综合结论来编排\n"
        f"- 明确区分不同论文的贡献与证据来源，但不要做僵硬的逐篇流水账\n"
        f"- 若源资料中包含图片、图表或实验结果，尽量保留并合理排版\n"
        f"- Speaker notes：每页100-200字口语化中文，讲综述内容，不要讲排版规范\n\n"
        f"完成标准（必须全部满足后才能结束）：\n"
        f"- 先完整执行 Step 6，再执行 Step 7，不要提前结束\n"
        f"- 必须生成完整讲稿文件 <project_path>/notes/total.md\n"
        f"- 必须执行 total_md_split.py，把 total.md 拆分为 notes/*.md\n"
        f"- 必须执行 finalize_svg.py 生成 svg_final/\n"
        f"- 必须执行 svg_to_pptx.py <project_path> -s final 导出 PPTX\n"
        f"- 结束前必须自检：notes/total.md、notes/*.md、svg_final/*.svg、*.pptx 都存在\n"
        f"- 如果缺少其中任何一项，不要输出总结，不要结束，继续补齐\n\n"
        f"以上配置已由用户在 Web 前端收集并确认，其余确认项已由系统按默认规则解析。"
        f"请直接完成到 svg_final 和 pptx 导出，不要调用 AskUserQuestion，也不要再询问任何问题。"
    )


def _build_multi_resume_prompt(project_dir: Path, merged_md_path: str, config: PptConfig) -> str:
    return (
        f"[BATCH_MODE]\n"
        f"/{SKILL_NAME}\n\n"
        f"请继续处理一个已经初始化但未完整完成的多篇综述 PPT 项目，不要重新新建项目，不要调用其他 skill。\n"
        f"当前项目目录：{project_dir}\n"
        f"主资料 Markdown：{merged_md_path}\n"
        f"模板：{config.template_prompt_value}\n"
        f"语言：{config.language}\n"
        f"受众：{config.audience}\n\n"
        f"当前问题：项目已有部分产物，但讲稿或最终导出不完整。\n"
        f"请在该项目目录内继续 Step 6/Step 7，补齐缺失产物，而不是从头再做一遍。\n\n"
        f"必须完成：\n"
        f"1. 若 notes/total.md 不存在，先补生成完整 speaker notes 到 notes/total.md\n"
        f"2. 若 notes/*.md 缺失，执行 total_md_split.py <project_path>\n"
        f"3. 若 svg_final/ 缺失或不完整，执行 finalize_svg.py <project_path>\n"
        f"4. 若 *.pptx 缺失，执行 svg_to_pptx.py <project_path> -s final\n"
        f"5. 完成前必须自检 notes/total.md、notes/*.md、svg_final/*.svg、*.pptx 均存在\n\n"
        f"执行约束：\n"
        f"- 当前是 Windows 后端任务，请不要假设 `python3` 命令存在\n"
        f"- 如需运行 Python 脚本，请优先使用这个解释器：{PYTHON}\n"
        f"- 使用绝对路径，不要询问用户，不要调用 AskUserQuestion\n"
        f"- 不要只输出说明或总结；缺什么就补什么，补齐后再结束\n"
    )


def _find_skill_file(skill_dir: Path) -> Path | None:
    for name in ("SKILL.md", "skill.md"):
        path = skill_dir / name
        if path.exists():
            return path
    return None


def get_cache_manifest_path(cache_dir: Path) -> Path:
    return cache_dir / CACHE_MANIFEST_NAME


def load_cached_project_outputs(cache_dir: Path) -> dict[str, str] | None:
    manifest_path = get_cache_manifest_path(cache_dir)
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("[ppt_generator] Failed to read PPT cache manifest: %s", manifest_path)
        return None

    required = ("project_dir", "ppt_path", "slides_dir", "notes_dir")
    if not all(isinstance(data.get(key), str) for key in required):
        return None

    project_dir = Path(data["project_dir"])
    ppt_path = Path(data["ppt_path"]) if data.get("ppt_path") else None
    slides_dir = Path(data["slides_dir"]) if data.get("slides_dir") else project_dir / "svg_final"
    notes_dir = Path(data["notes_dir"]) if data.get("notes_dir") else project_dir / "notes"
    merged_md = Path(data["merged_markdown_path"]) if data.get("merged_markdown_path") else project_dir / "sources" / "merged.md"

    if not project_dir.exists():
        return None
    if not slides_dir.exists() or not any(slides_dir.glob("*.svg")):
        return None
    if ppt_path and not ppt_path.exists():
        return None

    return {
        "project_dir": str(project_dir),
        "merged_markdown_path": str(merged_md) if merged_md.exists() else "",
        "ppt_path": str(ppt_path) if ppt_path else "",
        "slides_dir": str(slides_dir),
        "notes_dir": str(notes_dir) if notes_dir.exists() else "",
    }


def save_cached_project_outputs(cache_dir: Path, outputs: dict[str, str], cache_key: str) -> None:
    manifest_path = get_cache_manifest_path(cache_dir)
    payload = {
        **outputs,
        "cache_key": cache_key,
        "updated_at": int(time.time()),
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _list_dir(path: Path) -> str:
    if not path.exists():
        return f"(not found: {path})"
    items = sorted(path.iterdir(), key=lambda p: p.name)
    lines = []
    for p in items:
        if p.is_dir():
            sub = list(p.iterdir())
            lines.append(f"  📁 {p.name}/  ({len(sub)} items)")
        else:
            lines.append(f"  📄 {p.name}  ({p.stat().st_size:,} bytes)")
    return "\n".join(lines) if lines else "  (empty)"


def _find_recent_artifacts(search_dir: Path, since_ts: float) -> dict[str, list[Path]]:
    artifacts = {
        "notes": [],
        "svg_output": [],
        "svg_final": [],
        "pptx": [],
    }
    if not search_dir.exists():
        return artifacts

    for md in search_dir.rglob("*.md"):
        if md.parent.name == "notes" and md.stat().st_mtime >= since_ts - 5:
            artifacts["notes"].append(md)

    for svg in search_dir.rglob("*.svg"):
        if svg.stat().st_mtime < since_ts - 5:
            continue
        if svg.parent.name == "svg_output":
            artifacts["svg_output"].append(svg)
        elif svg.parent.name == "svg_final":
            artifacts["svg_final"].append(svg)

    for pptx in search_dir.rglob("*.pptx"):
        if pptx.name.endswith("_svg.pptx"):
            continue
        if pptx.stat().st_mtime >= since_ts - 5:
            artifacts["pptx"].append(pptx)

    return artifacts


async def _emit_stage_once(
    session_id: str,
    progress_cb,
    log_recorder,
    emitted: set[str],
    *,
    stage: str,
    label: str,
    pct: int,
    message: str,
    details: dict[str, Any],
) -> None:
    if stage in emitted:
        return
    emitted.add(stage)
    await progress_cb(session_id, "ppt", label, pct, stage=stage)
    await log_recorder.record(source="ppt", level="INFO", stage=stage, message=message, details=details)


async def _emit_detected_artifacts(
    session_id: str,
    output_dir: Path,
    progress_cb,
    log_recorder,
    since_ts: float,
    emitted: set[str],
) -> None:
    search_dirs = [output_dir, Path(REPO_ROOT) / "projects"]
    merged = {
        "notes": [],
        "svg_output": [],
        "svg_final": [],
        "pptx": [],
    }
    for search_dir in search_dirs:
        found = _find_recent_artifacts(search_dir, since_ts)
        for key in merged:
            merged[key].extend(found[key])

    if merged["notes"]:
        await _emit_stage_once(
            session_id,
            progress_cb,
            log_recorder,
            emitted,
            stage="notes_ready",
            label="生成讲稿...",
            pct=30,
            message="检测到讲稿文件",
            details={"count": len(merged["notes"]), "sample": str(merged["notes"][0])},
        )
    if merged["svg_output"]:
        await _emit_stage_once(
            session_id,
            progress_cb,
            log_recorder,
            emitted,
            stage="svg_output_ready",
            label="SVG 排版中...",
            pct=55,
            message="检测到 svg_output 产物",
            details={"count": len(merged["svg_output"]), "sample": str(merged["svg_output"][0])},
        )
    if merged["svg_final"]:
        await _emit_stage_once(
            session_id,
            progress_cb,
            log_recorder,
            emitted,
            stage="svg_final_ready",
            label="SVG 最终化...",
            pct=75,
            message="检测到 svg_final 产物",
            details={"count": len(merged["svg_final"]), "sample": str(merged["svg_final"][0])},
        )
    if merged["pptx"]:
        await _emit_stage_once(
            session_id,
            progress_cb,
            log_recorder,
            emitted,
            stage="pptx_ready",
            label="导出 PPTX...",
            pct=95,
            message="检测到 PPTX 产物",
            details={"count": len(merged["pptx"]), "sample": str(merged["pptx"][0])},
        )


async def _emit_phase_marker(
    session_id: str,
    marker: str,
    progress_cb,
    log_recorder,
    emitted: set[str],
) -> None:
    mapping = {
        "ppt_master_started": ("ppt_master_started", "开始生成 PPT...", 25, "进入 ppt-master 阶段"),
    }
    if marker not in mapping:
        await _emit_stage_once(
            session_id,
            progress_cb,
            log_recorder,
            emitted,
            stage="skill_marker",
            label="执行 skill 中...",
            pct=20,
            message="检测到 skill 阶段标记",
            details={"marker": marker},
        )
        return
    stage, label, pct, message = mapping[marker]
    await _emit_stage_once(
        session_id,
        progress_cb,
        log_recorder,
        emitted,
        stage=stage,
        label=label,
        pct=pct,
        message=message,
        details={"marker": marker},
    )


def describe_project_outputs(project_dir: Path, ppt_path: str | None = None) -> dict[str, str]:
    ppt_candidate = ppt_path or ""
    if not ppt_candidate:
        ppt_files = [p for p in project_dir.glob("*.pptx") if not p.name.endswith("_svg.pptx")]
        if not ppt_files:
            ppt_files = list(project_dir.glob("*.pptx"))
        if ppt_files:
            ppt_candidate = str(ppt_files[0])

    slides_dir = project_dir / "svg_final"
    notes_dir = project_dir / "notes"
    merged_md = project_dir / "sources" / "merged.md"
    total_md = notes_dir / "total.md"
    return {
        "project_dir": str(project_dir),
        "merged_markdown_path": str(merged_md) if merged_md.exists() else "",
        "ppt_path": ppt_candidate,
        "slides_dir": str(slides_dir) if slides_dir.exists() else "",
        "notes_dir": str(notes_dir) if notes_dir.exists() and total_md.exists() else "",
    }


def _read_text_source(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _find_markdown_for_source(sources_dir: Path, source_doc: SessionSourceDoc) -> Path | None:
    candidates = [
        sources_dir / f"{Path(source_doc.source_file_name).stem}.md",
        sources_dir / f"{Path(source_doc.pdf_path).stem}.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    normalized = Path(source_doc.source_file_name).stem.lower()
    for candidate in sorted(sources_dir.glob("*.md")):
        if candidate.name == "merged.md":
            continue
        if candidate.stem.lower() == normalized:
            return candidate
    return None


def _build_merged_markdown(sections: list[tuple[SessionSourceDoc, Path]]) -> str:
    blocks = ["# 多篇论文综述资料"]
    for source_doc, markdown_path in sections:
        body = _read_text_source(markdown_path)
        blocks.append(
            "\n".join([
                f"## 文献 {source_doc.order}：{Path(source_doc.source_file_name).stem}",
                f"- 来源文件：{source_doc.source_file_name}",
                f"- 文档编号：{source_doc.doc_id}",
                f"- 排序序号：{source_doc.order}",
                "",
                body,
            ])
        )
    return "\n\n---\n\n".join(blocks) + "\n"


def prepare_multi_project_sources(
    session_id: str,
    pdf_paths: list[str],
    project_dir: Path,
) -> tuple[Path, Path]:
    session = session_store.get_session(session_id)
    if session is None:
        raise RuntimeError(f"Session not found: {session_id}")
    if not session.source_documents:
        raise RuntimeError(f"No source documents registered for session {session_id}")

    run_skill_script("project_manager.py", "import-sources", str(project_dir), *pdf_paths)

    sources_dir = project_dir / "sources"
    merged_md_path = sources_dir / "merged.md"

    sections: list[tuple[SessionSourceDoc, Path]] = []
    updated_docs: list[SessionSourceDoc] = []
    for source_doc in sorted(session.source_documents, key=lambda doc: doc.order):
        markdown_path = _find_markdown_for_source(sources_dir, source_doc)
        if markdown_path is None:
            raise RuntimeError(f"Markdown not found for source document: {source_doc.source_file_name}")
        sections.append((source_doc, markdown_path))
        updated_docs.append(source_doc.model_copy(update={"markdown_path": str(markdown_path)}))

    merged_md_path.write_text(_build_merged_markdown(sections), encoding="utf-8")
    session_store.set_source_documents(session_id, updated_docs)
    session_store.set_merged_markdown_path(session_id, str(merged_md_path))
    return project_dir, merged_md_path


def _project_artifact_state(project_dir: Path) -> dict[str, Any]:
    design_spec = project_dir / "design_spec.md"
    notes_dir = project_dir / "notes"
    svg_output_dir = project_dir / "svg_output"
    svg_final_dir = project_dir / "svg_final"
    sources_dir = project_dir / "sources"
    total_md = notes_dir / "total.md"
    pptx_files = [p for p in project_dir.glob("*.pptx") if not p.name.endswith("_svg.pptx")]
    if not pptx_files:
        pptx_files = list(project_dir.glob("*.pptx"))

    notes = list(notes_dir.glob("*.md")) if notes_dir.exists() else []
    split_notes = [p for p in notes if p.name != "total.md"]
    svg_output = list(svg_output_dir.glob("*.svg")) if svg_output_dir.exists() else []
    svg_final = list(svg_final_dir.glob("*.svg")) if svg_final_dir.exists() else []
    source_files = list(sources_dir.iterdir()) if sources_dir.exists() else []

    has_total_md = total_md.exists()
    has_split_notes = bool(split_notes)
    has_svg_output = bool(svg_output)
    has_svg_final = bool(svg_final)
    has_pptx = bool(pptx_files)
    is_complete = has_total_md and has_split_notes and has_svg_final and has_pptx

    if is_complete:
        state = "final"
    elif has_svg_output or has_total_md or has_split_notes or design_spec.exists():
        state = "partial"
    else:
        state = "empty"

    newest_artifact_mtime = max(
        [project_dir.stat().st_mtime]
        + ([design_spec.stat().st_mtime] if design_spec.exists() else [])
        + ([p.stat().st_mtime for p in notes] if notes else [])
        + ([p.stat().st_mtime for p in svg_output] if svg_output else [])
        + ([p.stat().st_mtime for p in svg_final] if svg_final else [])
        + ([p.stat().st_mtime for p in pptx_files] if pptx_files else [])
    )

    return {
        "state": state,
        "design_spec": str(design_spec) if design_spec.exists() else "",
        "notes_count": len(notes),
        "split_notes_count": len(split_notes),
        "has_total_md": has_total_md,
        "svg_output_count": len(svg_output),
        "svg_final_count": len(svg_final),
        "pptx_count": len(pptx_files),
        "pptx_files": [str(p) for p in pptx_files],
        "source_files": [p.name for p in source_files],
        "is_complete": is_complete,
        "newest_artifact_mtime": newest_artifact_mtime,
    }


async def _emit_project_artifacts(
    session_id: str,
    project_dir: Path,
    progress_cb,
    log_recorder,
    emitted: set[str],
) -> None:
    notes = list((project_dir / "notes").glob("*.md")) if (project_dir / "notes").exists() else []
    svg_output = list((project_dir / "svg_output").glob("*.svg")) if (project_dir / "svg_output").exists() else []
    svg_final = list((project_dir / "svg_final").glob("*.svg")) if (project_dir / "svg_final").exists() else []
    pptx_files = [p for p in project_dir.glob("*.pptx") if not p.name.endswith("_svg.pptx")]
    if not pptx_files:
        pptx_files = list(project_dir.glob("*.pptx"))

    if notes:
        await _emit_stage_once(
            session_id,
            progress_cb,
            log_recorder,
            emitted,
            stage="notes_ready",
            label="生成讲稿...",
            pct=30,
            message="讲稿已就绪",
            details={"count": len(notes), "sample": str(notes[0])},
        )
    if svg_output:
        await _emit_stage_once(
            session_id,
            progress_cb,
            log_recorder,
            emitted,
            stage="svg_output_ready",
            label="SVG 排版中...",
            pct=55,
            message="svg_output 已就绪",
            details={"count": len(svg_output), "sample": str(svg_output[0])},
        )
    if svg_final:
        await _emit_stage_once(
            session_id,
            progress_cb,
            log_recorder,
            emitted,
            stage="svg_final_ready",
            label="SVG 最终化...",
            pct=75,
            message="svg_final 已就绪",
            details={"count": len(svg_final), "sample": str(svg_final[0])},
        )
    if pptx_files:
        await _emit_stage_once(
            session_id,
            progress_cb,
            log_recorder,
            emitted,
            stage="pptx_ready",
            label="导出 PPTX...",
            pct=95,
            message="PPTX 已导出",
            details={"count": len(pptx_files), "sample": str(pptx_files[0])},
        )


async def run_ppt_generation(
    session_id: str,
    pdf_path: str,
    config: PptConfig,
    output_dir: Path,
    progress_cb,
    log_recorder,
    *,
    prompt_override: str | None = None,
    project_search_dir: Path | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    skill_file = _find_skill_file(settings.skill_path)
    claude_exe = CLAUDE_CLI
    logger.info(
        "[PPT][%s] PRE-FLIGHT\n"
        "  REPO_ROOT       : %s  (exists=%s)\n"
        "  CLAUDE_CLI      : %s  (exists=%s)\n"
        "  skill directory : %s  (exists=%s)\n"
        "  skill file      : %s  (exists=%s)\n"
        "  pdf_path        : %s  (exists=%s)\n"
        "  output_dir      : %s",
        session_id,
        REPO_ROOT,
        Path(REPO_ROOT).exists(),
        claude_exe,
        claude_exe.exists() if claude_exe else False,
        settings.skill_path,
        settings.skill_path.exists(),
        skill_file,
        skill_file.exists() if skill_file else False,
        pdf_path,
        Path(pdf_path).exists(),
        output_dir,
    )
    if not claude_exe or not claude_exe.exists():
        raise GenerationError("Claude CLI not found. Set CLAUDE_CLI_PATH or add `claude` to PATH.", stage="preflight")
    if not skill_file:
        raise GenerationError(f"Skill file not found under: {settings.skill_path}", stage="preflight")

    prompt = prompt_override or _build_batch_prompt(pdf_path, config)
    cmd = [
        str(claude_exe),
        "--print",
        "--verbose",
        "--output-format",
        "stream-json",
        "--dangerously-skip-permissions",
        "--add-dir",
        str(output_dir),
        "--add-dir",
        str(Path(pdf_path).parent),
        "--add-dir",
        REPO_ROOT,
        "--model",
        "sonnet",
        prompt,
    ]

    env = dict(os.environ)
    if GIT_BASH and GIT_BASH.exists():
        env["CLAUDE_CODE_GIT_BASH_PATH"] = str(GIT_BASH)

    logger.info(
        "[PPT][%s] INVOKING SKILL  /%s  [BATCH_MODE]\n"
        "  cmd flags: %s\n"
        "  cwd: %s",
        session_id,
        SKILL_NAME,
        " ".join(str(c) for c in cmd),
        REPO_ROOT,
    )
    await log_recorder.record(
        source="ppt",
        level="INFO",
        stage="skill_invocation",
        message=f"已调用 /{SKILL_NAME} skill",
        details={"model": "sonnet", "output_dir": str(output_dir), "pdf_path": pdf_path},
    )
    await progress_cb(session_id, "ppt", "Claude 正在分析论文...", 10, stage="claude_started")
    await log_recorder.record(source="ppt", level="INFO", stage="claude_started", message="Claude CLI 已启动", details={"output_dir": str(output_dir)})

    loop = asyncio.get_running_loop()
    process_result: dict[str, Any] = {}
    proc_holder: dict[str, Any] = {"proc": None}
    started_at = time.time()
    emitted_stages: set[str] = {"claude_started"}
    last_output_at = {"ts": started_at}
    idle_warning_sent = {"value": False}

    import threading

    def _schedule_log(level: str, stage: str, message: str) -> None:
        if not message.strip():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                log_recorder.record(source="ppt", level=level, stage=stage, message=message),
                loop,
            )
        except RuntimeError:
            logger.exception("Failed to schedule Claude log forwarding for session %s", session_id)

    def _run() -> None:
        logger.info("[PPT][%s] ── Claude CLI process START ──", session_id)
        proc = _sp.Popen(
            cmd,
            stdout=_sp.PIPE,
            stderr=_sp.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=REPO_ROOT,
            env=env,
        )
        proc_holder["proc"] = proc

        _schedule_log("INFO", "claude_started", f"Claude 进程已创建 pid={proc.pid}")

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        def _read_stdout() -> None:
            assert proc.stdout
            for line in proc.stdout:
                line = line.rstrip("\n")
                stdout_lines.append(line)
                if line.strip():
                    last_output_at["ts"] = time.time()
                    idle_warning_sent["value"] = False
                    logger.info("[CLAUDE-OUT][%s] %s", session_id, line)
                    _schedule_log("INFO", "claude_output", line)

        def _read_stderr() -> None:
            assert proc.stderr
            for line in proc.stderr:
                line = line.rstrip("\n")
                stderr_lines.append(line)
                if line.strip():
                    last_output_at["ts"] = time.time()
                    idle_warning_sent["value"] = False
                    logger.warning("[CLAUDE-ERR][%s] %s", session_id, line)
                    _schedule_log("WARNING", "claude_error", line)

        t1 = threading.Thread(target=_read_stdout, daemon=True)
        t2 = threading.Thread(target=_read_stderr, daemon=True)
        t1.start()
        t2.start()

        try:
            proc.wait()
        finally:
            t1.join(30)
            t2.join(30)

        rc = proc.returncode
        stdout = "\n".join(stdout_lines)
        stderr = "\n".join(stderr_lines)
        logger.info(
            "[PPT][%s] ── Claude CLI process END ──  exit=%d  stdout_lines=%d  stderr_lines=%d",
            session_id,
            rc,
            len(stdout_lines),
            len(stderr_lines),
        )
        process_result["returncode"] = rc
        process_result["stdout"] = stdout
        process_result["stderr"] = stderr
        proc_holder["proc"] = None

    async def _run_with_monitoring() -> None:
        run_future = loop.run_in_executor(None, _run)
        while not run_future.done():
            idle_for = time.time() - last_output_at["ts"]
            if idle_for >= CLAUDE_IDLE_WARN_SECONDS and not idle_warning_sent["value"]:
                idle_warning_sent["value"] = True
                await log_recorder.record(
                    source="ppt",
                    level="WARNING",
                    stage="claude_idle",
                    message=f"Claude 进程仍在运行，但 {CLAUDE_IDLE_WARN_SECONDS} 秒内没有新的 stdout/stderr 输出；未终止，继续等待生成完成",
                )
                current_session = session_store.get_session(session_id)
                current_pct = current_session.progress.ppt_pct if current_session else 0
                await progress_cb(
                    session_id,
                    "ppt",
                    "仍在生成中，暂未收到新输出，继续等待...",
                    max(current_pct, 12),
                    stage="claude_idle",
                )

            await _emit_detected_artifacts(session_id, output_dir, progress_cb, log_recorder, started_at, emitted_stages)
            await asyncio.sleep(2)
        await run_future

    await _run_with_monitoring()

    rc = process_result.get("returncode", 1)
    stdout = process_result.get("stdout", "")
    stderr = process_result.get("stderr", "")

    if rc != 0 and not stdout.strip():
        raise GenerationError(
            f"Claude CLI exited {rc} with no output.",
            stage="claude_started",
            stdout=stdout,
            stderr=stderr,
        )

    await progress_cb(session_id, "ppt", "查找生成的项目...", 88, stage="artifact_discovery")
    await log_recorder.record(source="ppt", level="INFO", stage="artifact_discovery", message="查找生成的项目")

    projects_root = project_search_dir or (Path(REPO_ROOT) / "projects")
    logger.info("[PPT][%s] Searching for generated project under %s", session_id, projects_root)
    project_dir = _find_latest_project(projects_root)
    if not project_dir:
        logger.info("[PPT][%s] Not found in projects_root, trying output_dir: %s", session_id, output_dir)
        project_dir = _find_latest_project(output_dir)
    if not project_dir:
        raise GenerationError(
            "Claude CLI completed but no project directory was found under projects/ or cache output.",
            stage="artifact_discovery",
            stdout=stdout,
            stderr=stderr,
        )

    artifact_state = _project_artifact_state(project_dir)
    logger.info(
        "[PPT][%s] ✅ Project found: %s  state=%s\n%s",
        session_id,
        project_dir,
        artifact_state["state"],
        _list_dir(project_dir),
    )

    if artifact_state["state"] != "final":
        finalizer = settings.skill_path / "scripts" / "finalize_svg.py"
        splitter = settings.skill_path / "scripts" / "total_md_split.py"
        exporter = settings.skill_path / "scripts" / "svg_to_pptx.py"
        total_md = project_dir / "notes" / "total.md"
        notes_dir = project_dir / "notes"
        split_notes = [p for p in notes_dir.glob("*.md") if p.name != "total.md"] if notes_dir.exists() else []
        if total_md.exists() and not split_notes:
            _sp.run([PYTHON, str(splitter), str(project_dir)], cwd=REPO_ROOT, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if (project_dir / "svg_output").exists() and not (project_dir / "svg_final").exists():
            _sp.run([PYTHON, str(finalizer), str(project_dir)], cwd=REPO_ROOT, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if (project_dir / "svg_final").exists() and not any(p for p in project_dir.glob("*.pptx") if not p.name.endswith("_svg.pptx")):
            _sp.run([PYTHON, str(exporter), str(project_dir), "-s", "final"], cwd=REPO_ROOT, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
        artifact_state = _project_artifact_state(project_dir)

    outputs = describe_project_outputs(project_dir)
    outputs["project_dir"] = str(project_dir)
    session_store.update_path_fields(
        session_id,
        project_dir=outputs["project_dir"],
        merged_markdown_path=outputs.get("merged_markdown_path") or None,
        ppt_path=outputs["ppt_path"],
        slides_dir=outputs["slides_dir"],
        notes_dir=outputs["notes_dir"],
    )
    await _emit_project_artifacts(session_id, project_dir, progress_cb, log_recorder, emitted_stages)

    if artifact_state["state"] != "final":
        raise GenerationError(
            "Claude CLI completed and project directory was found, but only partial artifacts were generated (missing svg_final or PPTX export).",
            stage="artifact_discovery",
            stdout=stdout,
            stderr=stderr,
        )

    svg_final = project_dir / "svg_final"
    notes_dir = project_dir / "notes"
    pptx_files = list(project_dir.glob("*.pptx"))
    logger.info(
        "[PPT][%s] Artifacts summary:\n"
        "  svg_final/ : %d SVGs\n"
        "  notes/     : %d .md files\n"
        "  *.pptx     : %s",
        session_id,
        len(list(svg_final.glob("*.svg"))) if svg_final.exists() else 0,
        len(list(notes_dir.glob("*.md"))) if notes_dir.exists() else 0,
        [p.name for p in pptx_files],
    )

    logger.info("[PPT][%s] Project is kept at canonical location: %s", session_id, project_dir)

    await progress_cb(session_id, "ppt", "PPT 生成完成", 100, stage="complete", status="completed")
    await log_recorder.record(
        source="ppt",
        level="INFO",
        stage="complete",
        message="PPT 生成完成",
        details=outputs,
    )
    logger.info("[PPT][%s] Final project location:\n%s", session_id, _list_dir(project_dir))
    return project_dir


async def _resume_incomplete_multi_project(
    session_id: str,
    project_dir: Path,
    merged_md_path: Path,
    config: PptConfig,
    progress_cb,
    log_recorder,
) -> None:
    await progress_cb(session_id, "ppt", "继续补全讲稿与导出", 90, stage="resume_generation")
    await log_recorder.record(
        source="ppt",
        level="WARNING",
        stage="resume_generation",
        message="检测到多篇项目产物不完整，尝试继续补全讲稿与导出",
        details={"project_dir": str(project_dir)},
    )
    resume_prompt = _build_multi_resume_prompt(project_dir, str(merged_md_path), config)
    await run_ppt_generation(
        session_id,
        str(merged_md_path),
        config,
        project_dir.parent,
        progress_cb,
        log_recorder,
        prompt_override=resume_prompt,
        project_search_dir=project_dir.parent,
    )


async def run_multi_ppt_generation(
    session_id: str,
    pdf_paths: list[str],
    config: PptConfig,
    output_dir: Path,
    progress_cb,
    log_recorder,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    session = session_store.get_session(session_id)
    if session is None:
        raise GenerationError(f"Session not found: {session_id}", stage="preflight")

    await progress_cb(session_id, "ppt", "初始化综述项目", 10, stage="project_init")
    await log_recorder.record(source="ppt", level="INFO", stage="project_init", message="初始化多篇综述项目")

    project_name = f"multi_survey_{session_id[:8]}"
    project_dir_raw = run_skill_script(
        "project_manager.py",
        "init",
        project_name,
        "--format",
        "ppt169",
        "--dir",
        str(output_dir),
    )
    project_dir_line = next((line for line in reversed(project_dir_raw.splitlines()) if line.startswith("Project created:")), "")
    if project_dir_line:
        project_dir = Path(project_dir_line.split(":", 1)[1].strip())
    else:
        project_dir = _find_latest_project(output_dir)
    if not project_dir:
        raise GenerationError("Failed to initialize multi-source project directory", stage="project_init")

    session_store.update_path_fields(session_id, project_dir=str(project_dir))

    await progress_cb(session_id, "ppt", "导入多篇 PDF", 20, stage="import_sources")
    await log_recorder.record(
        source="ppt",
        level="INFO",
        stage="import_sources",
        message="开始导入多篇 PDF 到 sources",
        details={"count": len(pdf_paths)},
    )
    _, merged_md_path = prepare_multi_project_sources(session_id, pdf_paths, project_dir)
    session_store.update_path_fields(session_id, merged_markdown_path=str(merged_md_path))
    await log_recorder.record(
        source="ppt",
        level="INFO",
        stage="merge_markdown",
        message="已生成 merged markdown",
        details={"merged_markdown_path": str(merged_md_path)},
    )
    await progress_cb(session_id, "ppt", "整理综述资料", 28, stage="merge_markdown")

    multi_prompt = _build_multi_batch_prompt(str(merged_md_path), config)
    final_project_dir = await run_ppt_generation(
        session_id,
        str(merged_md_path),
        config,
        project_dir.parent,
        progress_cb,
        log_recorder,
        prompt_override=multi_prompt,
        project_search_dir=project_dir.parent,
    )

    artifact_state = _project_artifact_state(final_project_dir)
    if artifact_state["state"] != "final":
        await _resume_incomplete_multi_project(
            session_id,
            final_project_dir,
            merged_md_path,
            config,
            progress_cb,
            log_recorder,
        )
        artifact_state = _project_artifact_state(final_project_dir)
        if artifact_state["state"] != "final":
            raise GenerationError(
                "Multi-source PPT generation finished with incomplete artifacts (speaker notes or final export still missing).",
                stage="resume_generation",
            )

    return final_project_dir


def _find_latest_project(search_dir: Path) -> Path | None:
    if not search_dir or not search_dir.exists():
        return None

    ranked: list[tuple[int, float, Path]] = []
    for d in search_dir.iterdir():
        if not d.is_dir():
            continue
        artifact_state = _project_artifact_state(d)
        if artifact_state["state"] == "empty":
            continue
        score = 2 if artifact_state["state"] == "final" else 1
        ranked.append((score, d.stat().st_mtime, d))

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return ranked[0][2] if ranked else None
