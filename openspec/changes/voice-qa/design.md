## Context

`ChatPanel.tsx` is a self-contained component that handles text Q&A. It calls `POST /api/chat` and renders message bubbles with collapsible source cards. `PptViewerPage.tsx` manages slide navigation state (`current`, `setCurrent`). The two components are currently independent — ChatPanel doesn't know about slide state.

The browser's `SpeechRecognition` API (standard: `window.SpeechRecognition || window.webkitSpeechRecognition`) enables microphone-based STT. `window.speechSynthesis` enables TTS. Both are available in Chrome/Edge without any backend involvement.

## Goals / Non-Goals

**Goals:**
- Microphone button in ChatPanel that captures voice and submits as text question
- TTS playback of assistant answers (opt-in, user toggleable)
- Source card "跳转" button that jumps PPT viewer to the cited slide/page
- Graceful degradation when browser doesn't support SpeechRecognition

**Non-Goals:**
- Custom server-side STT (Whisper etc.) — browser native is sufficient for MVP
- Wake word detection or continuous listening mode
- Streaming TTS during LLM response generation

## Decisions

**Decision 1: Lift slide navigation to PptViewerPage, pass callback to ChatPanel**
Currently `ChatPanel` has no way to control slide navigation. The cleanest solution is: `PptViewerPage` passes an `onJumpToSlide(page: number)` callback prop to `ChatPanel`. When user clicks a source card's jump button, ChatPanel calls this callback. This avoids global state management.

**Decision 2: Browser SpeechRecognition, not server-side**
Chosen for zero latency, zero cost, and no extra backend infrastructure. Chinese recognition works well in Chrome with `lang="zh-CN"`. The microphone permission prompt is handled by the browser.

**Decision 3: TTS toggle in ChatPanel header**
Add a small speaker icon toggle in ChatPanel header. When enabled, each new assistant message is automatically read aloud. The toggle state is local component state (not persisted). Default: OFF (not everyone wants auto-play).

**Decision 4: Page-to-slide mapping**
Source cards include a `page` number from the PDF. The PPTX slide index is independent. We'll treat the page number as a slide index hint — if `page <= slides.length`, jump to that slide index. This is approximate but useful.

## Risks / Trade-offs

- [Risk] `SpeechRecognition` not supported in Firefox/Safari → Mitigation: check availability; hide mic button if not supported, show tooltip "请使用 Chrome 或 Edge"
- [Risk] Microphone permission denied by user → Mitigation: catch `NotAllowedError` and show friendly error message
- [Risk] Page number from RAG source != PPTX slide number → Mitigation: Jump button is best-effort; label it "约第 N 页" to set expectations
- [Risk] TTS overlapping — user clicks new message while previous is still reading → Mitigation: cancel previous utterance before starting new one
