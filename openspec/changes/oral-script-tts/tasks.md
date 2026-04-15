## 1. Backend: Data Model

- [x] 1.1 Add `script: list[str] | None = None` field to `SessionData` in `app/models.py`
- [x] 1.2 Add `set_script(session_id, script)` and expose `script` in `get_session()` return in `app/services/session_store.py`

## 2. Backend: Script Generation Service

- [x] 2.1 Create `app/services/script_gen.py` with `extract_slide_texts(pptx_path) -> list[str]` using `python-pptx`
- [x] 2.2 Add `generate_narrations(slide_texts: list[str]) -> list[str]` in `script_gen.py` — calls LLM in parallel with `asyncio.gather` for each slide
- [x] 2.3 Handle empty slides: return placeholder "此页为图表页，请参考幻灯片内容" when slide text is blank

## 3. Backend: Script API Endpoint

- [x] 3.1 Create `app/api/script.py` with `POST /api/sessions/{id}/script` — checks for cached script, otherwise calls `generate_narrations` and stores result
- [x] 3.2 Add `GET /api/sessions/{id}/script` in `script.py` — returns cached script or 404 if not yet generated
- [x] 3.3 Register `script` router in `backend/main.py`
- [x] 3.4 Verify `python-pptx` is in `requirements.txt` (add if missing)

## 4. Frontend: Fetch and Cache Script

- [x] 4.1 In `PptViewerPage.tsx`, after PPT loads successfully, call `POST /api/sessions/{id}/script` to trigger generation, then store the returned script array in component state
- [x] 4.2 Show a subtle "生成讲稿中..." indicator while script is generating; hide on completion

## 5. Frontend: Narration Display

- [x] 5.1 Add collapsible narration panel below slide display in `PptViewerPage.tsx` — shows current slide's narration text
- [x] 5.2 Panel defaults to collapsed; toggle button shows "讲稿 ▼" / "讲稿 ▲"
- [x] 5.3 When current slide index changes, update narration panel content to matching narration string

## 6. Frontend: TTS Playback Controls

- [x] 6.1 Detect `window.speechSynthesis` availability on mount; store in state
- [x] 6.2 Add "播报" button in slide controls bar (only visible when `speechSynthesis` is available and narration exists)
- [x] 6.3 On "播报" click: call `speechSynthesis.speak(new SpeechSynthesisUtterance(narration))`, update button to "停止"
- [x] 6.4 On "停止" click: call `speechSynthesis.cancel()`, reset button to "播报"
- [x] 6.5 Handle `utterance.onend` event to reset button state when TTS finishes naturally
