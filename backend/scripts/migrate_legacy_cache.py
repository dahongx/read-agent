"""一次性迁移脚本：

1. 把 <repo>/projects/zep_temporal_kg_memory_ppt169_20260525/ 整个目录拷到
   backend/uploads/cache/ppt/d26f7eb599540e8b-b5a08452/zep_temporal_kg_memory_ppt169_20260525/
   （如果还没拷过）

2. 重写 backend/uploads/cache/ppt/<space_id>/project_manifest.json，
   把所有路径改成相对 cache_dir 的 POSIX 路径。
   涉及的 space：
     - d26f7eb599540e8b-b5a08452（单篇）
     - 5fafbc5d7f062de6-b5a08452-86e9e44e（多篇）

3. 修复 backend/uploads/spaces/<space_id>.json 里的绝对路径字段（pdf_path / source_documents.pdf_path），
   让它们也变成 backend/uploads/sessions/... 下的相对路径（相对 REPO_ROOT），
   避免 git clone 到服务器后引用 E:\\... 找不到文件。

跑一次就够了。安全：所有改动幂等，重跑只会确认一遍。
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # backend/scripts/migrate_legacy_cache.py 上两层
UPLOADS = REPO_ROOT / "backend" / "uploads"
PROJECTS_DIR = REPO_ROOT / "projects"

DEMO_SPACES = [
    "d26f7eb599540e8b-b5a08452",
    "5fafbc5d7f062de6-b5a08452-86e9e44e",
]
LEGACY_SINGLE_PROJECT = "zep_temporal_kg_memory_ppt169_20260525"
LEGACY_SINGLE_SPACE = "d26f7eb599540e8b-b5a08452"


def _to_posix_relative(target: str | None, base: Path) -> str:
    """把 target 转成相对 base 的 POSIX 路径；不在 base 下时退化为相对 REPO_ROOT。"""
    if not target:
        return ""
    p = Path(target)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(base.resolve()).as_posix()
        except (ValueError, OSError):
            try:
                return p.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
            except (ValueError, OSError):
                return p.as_posix()
    return p.as_posix()


def _normalize_to_repo_relative(target: str | None) -> str:
    """把绝对路径转成相对 REPO_ROOT 的 POSIX 路径，用于 spaces/<id>.json 里的 pdf_path 等。"""
    if not target:
        return target or ""
    p = Path(target)
    if not p.is_absolute():
        return p.as_posix()
    try:
        return p.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except (ValueError, OSError):
        return p.as_posix()


def step_copy_legacy_project() -> None:
    src = PROJECTS_DIR / LEGACY_SINGLE_PROJECT
    dst_root = UPLOADS / "cache" / "ppt" / LEGACY_SINGLE_SPACE
    dst = dst_root / LEGACY_SINGLE_PROJECT

    if not src.exists():
        print(f"[skip] legacy project not found: {src}")
        return

    if dst.exists():
        print(f"[ok]   legacy project already migrated: {dst}")
        return

    dst_root.mkdir(parents=True, exist_ok=True)
    print(f"[copy] {src}  ->  {dst}")
    shutil.copytree(src, dst)


def step_rewrite_manifest(space_id: str) -> None:
    cache_dir = UPLOADS / "cache" / "ppt" / space_id
    manifest = cache_dir / "project_manifest.json"
    if not manifest.exists():
        print(f"[skip] no manifest for {space_id}")
        return

    data = json.loads(manifest.read_text(encoding="utf-8"))

    # 找最新的 project 子目录
    project_subdirs = sorted(
        (p for p in cache_dir.iterdir() if p.is_dir() and p.name != "_pycache_"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # 优先用 manifest 已有的 project_dir 名；如果不在，就取最新子目录
    legacy_project_dir = data.get("project_dir") or ""
    project_name = Path(legacy_project_dir).name if legacy_project_dir else ""
    project_dir = (cache_dir / project_name) if project_name else None
    if project_dir is None or not project_dir.exists():
        if not project_subdirs:
            print(f"[warn] no project subdir under {cache_dir}, manifest unchanged")
            return
        project_dir = project_subdirs[0]
        project_name = project_dir.name

    # 构造产物相对路径
    pptx_files = [p for p in project_dir.glob("*.pptx") if not p.name.endswith("_svg.pptx")]
    if not pptx_files:
        pptx_files = list(project_dir.glob("*.pptx"))
    ppt_path = str(pptx_files[0]) if pptx_files else ""

    slides_dir = project_dir / "svg_final"
    notes_dir = project_dir / "notes"
    merged_md = project_dir / "sources" / "merged.md"

    new_data = {
        "project_dir": _to_posix_relative(str(project_dir), cache_dir),
        "merged_markdown_path": _to_posix_relative(str(merged_md) if merged_md.exists() else "", cache_dir),
        "ppt_path": _to_posix_relative(ppt_path, cache_dir),
        "slides_dir": _to_posix_relative(str(slides_dir) if slides_dir.exists() else "", cache_dir),
        "notes_dir": _to_posix_relative(str(notes_dir) if notes_dir.exists() else "", cache_dir),
        "cache_key": data.get("cache_key") or space_id,
        "updated_at": data.get("updated_at"),
    }
    manifest.write_text(json.dumps(new_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[rewr] manifest -> {manifest}")
    for k, v in new_data.items():
        print(f"         {k}: {v}")


def step_rewrite_space_metadata(space_id: str) -> None:
    space_path = UPLOADS / "spaces" / f"{space_id}.json"
    if not space_path.exists():
        print(f"[skip] no space.json for {space_id}")
        return

    data = json.loads(space_path.read_text(encoding="utf-8"))
    changed = False

    if data.get("pdf_path"):
        rel = _normalize_to_repo_relative(data["pdf_path"])
        if rel != data["pdf_path"]:
            data["pdf_path"] = rel
            changed = True

    if isinstance(data.get("source_documents"), list):
        for doc in data["source_documents"]:
            if isinstance(doc, dict) and doc.get("pdf_path"):
                rel = _normalize_to_repo_relative(doc["pdf_path"])
                if rel != doc["pdf_path"]:
                    doc["pdf_path"] = rel
                    changed = True

    # 早期 space.json 没有 state 字段，对应产物完整就标 ready
    if not data.get("state"):
        manifest = UPLOADS / "cache" / "ppt" / space_id / "project_manifest.json"
        if manifest.exists():
            data["state"] = "ready"
            changed = True

    if changed:
        space_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[rewr] space    -> {space_path}")
    else:
        print(f"[ok]   space already portable: {space_path.name}")


def main() -> int:
    print(f"[init] REPO_ROOT = {REPO_ROOT}")
    print(f"[init] UPLOADS   = {UPLOADS}")

    step_copy_legacy_project()
    for sid in DEMO_SPACES:
        step_rewrite_manifest(sid)
        step_rewrite_space_metadata(sid)

    print("\n[done] migration complete. Verify by starting backend and opening each space in the browser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
