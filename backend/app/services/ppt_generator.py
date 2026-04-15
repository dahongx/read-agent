from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import shutil
import subprocess as _sp
import sys
from pathlib import Path

from app.core.config import settings
from app.models import PptConfig

logger = logging.getLogger(__name__)

CLAUDE_CLI = settings.claude_cli_path
GIT_BASH = settings.git_bash_path
PYTHON = sys.executable
REPO_ROOT = str(settings.project_root)
SKILL_NAME = settings.skill_path.name

logger.info("[ppt_generator] REPO_ROOT resolved to: %s", REPO_ROOT)
logger.info(
    "[ppt_generator] CLAUDE_CLI: %s  exists=%s",
    CLAUDE_CLI,
    CLAUDE_CLI.exists() if CLAUDE_CLI else False,
)


def compute_cache_key(pdf_path: str, config: PptConfig) -> str:
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    pdf_hash = h.hexdigest()[:16]
    config_hash = hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:8]
    return f"{pdf_hash}-{config_hash}"


def run_skill_script(script_name: str, *args: str, allow_partial_failure: bool = False) -> str:
    script_path = settings.skill_path / "scripts" / script_name
    cmd = [PYTHON, str(script_path)] + list(args)
    logger.info("Running: %s", " ".join(cmd))
    result = _sp.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0 and not allow_partial_failure:
        raise RuntimeError(f"{script_name} failed (exit {result.returncode}):\n{result.stderr[-2000:]}")
    if result.returncode != 0:
        logger.warning("%s exited with %d:\n%s", script_name, result.returncode, result.stderr[-500:])
    return result.stdout


def _build_batch_prompt(pdf_path: str, config: PptConfig) -> str:
    return (
        f"[BATCH_MODE] /{SKILL_NAME}\n\n"
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
        f"请将这些内容视为最终确认结果，直接执行完整流程，不要调用 AskUserQuestion，也不要再询问任何问题。"
    )


def _find_skill_file(skill_dir: Path) -> Path | None:
    for name in ("SKILL.md", "skill.md"):
        path = skill_dir / name
        if path.exists():
            return path
    return None


def _list_dir(path: Path) -> str:
    """Return a human-readable one-level listing for logging."""
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


async def run_paper_to_ppt(
    session_id: str,
    pdf_path: str,
    config: PptConfig,
    output_dir: Path,
    broadcast_fn,
) -> Path:
    """
    Run paper-to-ppt skill via Claude CLI --print mode.
    - Verifies skill file exists before invoking.
    - Streams Claude CLI output line-by-line to logger.
    - Moves generated project into output_dir (cache_dir) after completion.
    """
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
        raise RuntimeError("Claude CLI not found. Set CLAUDE_CLI_PATH or add `claude` to PATH.")
    if not skill_file:
        raise RuntimeError(f"Skill file not found under: {settings.skill_path}")

    prompt = _build_batch_prompt(pdf_path, config)

    cmd = [
        str(claude_exe),
        "--print",
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
        " ".join(str(c) for c in cmd[:-1]),
        REPO_ROOT,
    )
    await broadcast_fn(session_id, "ppt", "Claude 正在分析论文...", 12)

    loop = asyncio.get_event_loop()
    process_result: dict = {}

    import threading

    def _run():
        """Run Claude CLI and stream stdout/stderr line-by-line to logger."""
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

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        def _read_stdout():
            assert proc.stdout
            for line in proc.stdout:
                line = line.rstrip("\n")
                stdout_lines.append(line)
                if line.strip():
                    logger.info("[CLAUDE-OUT][%s] %s", session_id, line)

        def _read_stderr():
            assert proc.stderr
            for line in proc.stderr:
                line = line.rstrip("\n")
                stderr_lines.append(line)
                if line.strip():
                    logger.warning("[CLAUDE-ERR][%s] %s", session_id, line)

        t1 = threading.Thread(target=_read_stdout, daemon=True)
        t2 = threading.Thread(target=_read_stderr, daemon=True)
        t1.start()
        t2.start()

        try:
            proc.wait(timeout=2400)
        except _sp.TimeoutExpired:
            proc.kill()
            t1.join(5)
            t2.join(5)
            raise RuntimeError("Claude CLI timed out after 40 min")

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

    async def _run_with_progress():
        run_future = loop.run_in_executor(None, _run)
        pct = 15
        while not run_future.done():
            await asyncio.sleep(30)
            if not run_future.done():
                pct = min(pct + 3, 85)
                await broadcast_fn(session_id, "ppt", "生成中...", pct)
        await run_future

    await _run_with_progress()

    rc = process_result.get("returncode", 1)
    stdout = process_result.get("stdout", "")
    stderr = process_result.get("stderr", "")

    if rc != 0 and not stdout.strip():
        raise RuntimeError(f"Claude CLI exited {rc} with no output.\nstderr: {stderr[-1000:]}")

    await broadcast_fn(session_id, "ppt", "查找生成的项目...", 88)

    projects_root = Path(REPO_ROOT) / "projects"
    logger.info("[PPT][%s] Searching for generated project under %s", session_id, projects_root)
    project_dir = _find_latest_project(projects_root)
    if not project_dir:
        logger.info("[PPT][%s] Not found in projects_root, trying output_dir: %s", session_id, output_dir)
        project_dir = _find_latest_project(output_dir)
    if not project_dir:
        raise RuntimeError(
            f"Claude CLI completed (exit={rc}) but no project with svg_final/ found.\n"
            f"Searched: {projects_root}  AND  {output_dir}\n"
            f"stdout tail: {stdout[-800:]}"
        )

    logger.info("[PPT][%s] ✅ Project found: %s\n%s", session_id, project_dir, _list_dir(project_dir))
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

    if project_dir.parent.resolve() != output_dir.resolve():
        dest = output_dir / project_dir.name
        logger.info(
            "[PPT][%s] Moving project into cache_dir\n  from: %s\n  to  : %s",
            session_id,
            project_dir,
            dest,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(project_dir), str(dest))
            project_dir = dest
            logger.info("[PPT][%s] Move complete → %s", session_id, project_dir)
        except Exception as e:
            logger.warning("[PPT][%s] Move failed (%s), using original location", session_id, e)
    else:
        logger.info("[PPT][%s] Project already in cache_dir: %s", session_id, project_dir)

    logger.info("[PPT][%s] Final project location:\n%s", session_id, _list_dir(project_dir))
    return project_dir


def _find_latest_project(search_dir: Path) -> Path | None:
    if not search_dir or not search_dir.exists():
        return None
    candidates = sorted(
        [
            d
            for d in search_dir.iterdir()
            if d.is_dir() and (d / "svg_final").exists() and any((d / "svg_final").glob("*.svg"))
        ],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None