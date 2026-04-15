## 1. Backend: Full-Context Service

- [ ] 1.1 Create `app/services/full_context.py` with `get_full_context(session_id) -> tuple[str, str, int]` returning `(context_text, pdf_filename, page_count)` — reads docstore.json from `rag_index_path`, sorts chunks by page_label, formats as `[第N页]\n{text}\n\n`
- [ ] 1.2 Add token count estimate (chars // 4) and return early with fallback signal if > 80K tokens
- [ ] 1.3 Handle missing `rag_index_path` gracefully: return empty string (caller falls back to DEV_MODE)

## 2. Backend: Update Chat Endpoint

- [ ] 2.1 In `app/api/chat.py`, replace `retrieve()` call with `get_full_context()` for real-mode sessions
- [ ] 2.2 Update system prompt: add instruction "引用论文内容时，在句末用(第N页)标注页码来源，N为具体页码数字"
- [ ] 2.3 Add `_parse_citations(answer: str, pdf_filename: str) -> list[Source]` function: uses `re.findall(r'第(\d{1,3})页', answer)` to extract page numbers, creates Source objects with surrounding text snippet
- [ ] 2.4 Replace `sources` in response with parsed citations from `_parse_citations(answer)`
- [ ] 2.5 Keep DEV_MODE_RAG fallback path unchanged (design_spec.md)

## 3. Frontend: PDF Viewer Modal Component

- [ ] 3.1 Create `frontend/src/components/PdfViewer.tsx` — accepts `{ sessionId, page, onClose }` props
- [ ] 3.2 Render a fixed full-screen overlay (`fixed inset-0 bg-black/50 z-50`) with centered modal (`80vw × 85vh`)
- [ ] 3.3 Inside modal: close button (×) in top-right corner, title "第N页 · 原文", iframe filling remaining space
- [ ] 3.4 iframe src = `/api/sessions/${sessionId}/pdf#page=${page}`, `allow="fullscreen"`
- [ ] 3.5 Clicking overlay background calls `onClose`; pressing Escape key calls `onClose`

## 4. Frontend: Inline Citations in ChatPanel

- [ ] 4.1 Add `PdfViewerState` state (`{ page: number } | null`) to `ChatPanel`
- [ ] 4.2 Create `renderAnswerWithCitations(text: string, onCiteClick: (page: number) => void): ReactNode` — splits text on `/(第\d{1,3}页)/g`, renders plain parts as text and matches as `<button>` badges
- [ ] 4.3 In `AssistantMessage`, replace plain `{msg.content}` with `renderAnswerWithCitations(msg.content, ...)`
- [ ] 4.4 When a citation badge is clicked, set `PdfViewerState` to `{ page: N }`
- [ ] 4.5 Render `<PdfViewer>` modal when `PdfViewerState !== null`; close sets it back to `null`
- [ ] 4.6 Remove the existing "查看引用" expand/collapse section — citations are now inline (keep SourceCard for future use but don't render it in AssistantMessage)
