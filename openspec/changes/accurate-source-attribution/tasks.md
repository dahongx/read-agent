## 1. Backend: Citation-based source attribution
- [x] 1.1 Update system prompt in `chat.py` — require `(第N页)` inline citation per point, with example
- [x] 1.2 Add `_parse_citations(answer, retrieved)` — extracts page numbers from LLM answer, maps to retrieved chunks
- [x] 1.3 Replace top-k sources with citation-parsed sources in chat response; fallback to top-k if LLM cites nothing

## 2. Frontend: Inline citation badges
- [x] 2.1 Add `renderWithCitations(text, onPageClick)` in `ChatPanel.tsx` — splits on `(第N页)` / `（第N页）`, renders each as a clickable blue badge
- [x] 2.2 Remove bottom source card list from `AssistantMessage` — citations are now inline only
- [x] 2.3 Remove `SourceCard` component (no longer needed)

## 3. Frontend: PDF viewer page navigation
- [x] 3.1 Add `?_=${page}` cache-busting to iframe src in `PdfViewer.tsx`
- [x] 3.2 Add `key={page}` to iframe to force remount on page change
- [x] 3.3 Add "↗ 新标签页" button as reliable fallback

## Notes
- Reference page filtering was explored and reverted — not needed since citation-based attribution already excludes irrelevant pages naturally
- Cache version remains `v3` in `task_manager.py` (v2 paragraph chunking + paper_title metadata)
