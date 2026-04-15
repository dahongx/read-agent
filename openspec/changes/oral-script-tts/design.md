## Context

The PPT viewer (`PptViewerPage.tsx`) currently renders slides extracted from the PPTX file via `pptx2html`. Each slide is displayed as raw HTML. The LLM (GLM-4-Flash via ZhipuAI) is already wired for chat Q&A. The browser's native `SpeechSynthesis` API can read text aloud without any extra dependency. Session state is stored in-memory in `session_store.py`.

The challenge is extracting text content from each slide to feed the LLM for narration generation. Currently `pptx2html` outputs HTML blobs — text can be extracted from these on the frontend. For the backend narration API, we need the raw slide text extracted server-side from the PPTX file using `python-pptx`.

## Goals / Non-Goals

**Goals:**
- Generate one narration string per slide using LLM
- Cache narrations in session store to avoid re-generation
- Play narrations via browser `SpeechSynthesis` with play/stop controls
- Display narration text below each slide (collapsible)
- Optionally auto-advance slides when narration ends

**Non-Goals:**
- Custom TTS voice cloning or high-quality neural TTS (browser SpeechSynthesis is sufficient for MVP)
- Background music or sound effects
- Syncing narration word-by-word with slide animations
- Streaming narration generation (generate all at once is fine)

## Decisions

**Decision 1: Server-side vs client-side text extraction**
Extract slide text server-side using `python-pptx`, not client-side from HTML blobs. Rationale: The HTML from `pptx2html` may have noise (style tags, inline styles). `python-pptx` gives clean structured text per shape per slide. The PPTX file is already stored on disk per session.

**Decision 2: Generate all narrations in one API call**
`POST /api/sessions/{id}/script` triggers generation of ALL slide narrations in a single request (parallel LLM calls per slide using `asyncio.gather`). Rationale: The frontend requests narrations lazily would cause latency on first play. Generating all upfront is simpler and the PPTX typically has 10-30 slides.

**Decision 3: Browser SpeechSynthesis over server-side TTS**
Use `window.speechSynthesis` (Web Speech API). Rationale: Zero extra dependencies, works offline, no API cost. Trade-off: Voice quality is lower than neural TTS, but acceptable for MVP.

**Decision 4: Cache in session store**
Store generated narrations in `SessionData` as `script: list[str] | None`. Return cached version if already generated. Client-side also caches to avoid re-fetch.

## Risks / Trade-offs

- [Risk] `python-pptx` text extraction may miss content in grouped shapes or SmartArt → Mitigation: Best-effort extraction, empty slides get a placeholder narration ("此页无文字内容")
- [Risk] Browser SpeechSynthesis availability varies by browser/OS → Mitigation: Show text as fallback; hide TTS buttons if `speechSynthesis` not available
- [Risk] LLM cost for 20-slide deck (20 calls) → Mitigation: Cache in session; GLM-4-Flash is very cheap per call

## Migration Plan

1. Add `script` field to `SessionData` model (optional, default None)
2. Create `app/services/script_gen.py` with `extract_slide_texts()` and `generate_narrations()`
3. Add `app/api/script.py` with GET and POST endpoints
4. Register routes in `main.py`
5. Update `PptViewerPage.tsx` to fetch script on load and add TTS controls
