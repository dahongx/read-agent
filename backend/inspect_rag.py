"""
查看 RAG 知识库内容
用法（在 backend/ 目录下运行）：
  python inspect_rag.py
"""
import json
import sys
from pathlib import Path


def find_best_index(uploads: Path) -> Path | None:
    # Prefer rag_cache dirs
    cache_root = uploads / "rag_cache"
    if cache_root.exists():
        dirs = [d for d in cache_root.iterdir() if (d / "docstore.json").exists()]
        if dirs:
            return sorted(dirs, key=lambda d: d.stat().st_mtime, reverse=True)[0]
    # Fall back to session rag_index dirs
    for session_dir in sorted(uploads.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True):
        if session_dir.name == "rag_cache":
            continue
        idx = session_dir / "rag_index"
        if (idx / "docstore.json").exists():
            return idx
    return None


def inspect(index_dir: Path):
    docstore_path = index_dir / "docstore.json"
    raw = json.loads(docstore_path.read_text(encoding="utf-8"))

    # LlamaIndex stores data under 'docstore/data'
    data_section: dict = raw.get("docstore/data", {})
    meta_section: dict = raw.get("docstore/metadata", {})

    print(f"\nIndex dir : {index_dir}")
    print(f"Chunks    : {len(data_section)}")
    print(f"Metadata  : {len(meta_section)} entries")

    vs_path = index_dir / "default__vector_store.json"
    if vs_path.exists():
        vs = json.loads(vs_path.read_text(encoding="utf-8"))
        emb_dict = vs.get("embedding_dict", {})
        if emb_dict:
            sample = next(iter(emb_dict.values()))
            print(f"Vectors   : {len(emb_dict)}  dim={len(sample)}")

    print("\n" + "=" * 60)
    shown = 0
    for doc_id, doc in data_section.items():
        inner = doc.get("__data__", {})
        text: str = inner.get("text", "")
        meta: dict = inner.get("metadata", {})
        if not text.strip():
            continue
        page = meta.get("page_label") or meta.get("page_number", "?")
        file_name = meta.get("file_name", "?")
        safe_text = text[:300].encode("gbk", errors="replace").decode("gbk")
        print(f"[{shown+1}] file={file_name}  page={page}  chars={len(text)}")
        print(f"     {safe_text.replace(chr(10), ' ')}{'...' if len(text) > 300 else ''}")
        print()
        shown += 1
        if shown >= 15:
            print(f"... (showing 15/{len(data_section)} chunks)")
            break


def main():
    uploads = Path(__file__).parent / "uploads"
    if len(sys.argv) > 1:
        index_dir = Path(sys.argv[1])
    else:
        index_dir = find_best_index(uploads)
        if index_dir is None:
            print("No index found. Upload a PDF first.")
            return
    inspect(index_dir)


if __name__ == "__main__":
    main()
