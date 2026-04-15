## Why

PRD Feature 3 & 4 require that the system generate an oral script for each PPT slide and read it aloud (TTS). Currently the PPT viewer shows slides with no narration; users must read silently. This change adds LLM-generated slide narrations and browser-based TTS playback, making the presentation experience fully voiced.

## What Changes

- **Backend**: New `POST /api/sessions/{id}/script` endpoint that calls LLM for each slide to generate a concise oral narration, returns an array of per-slide narration strings.
- **Backend**: New `GET /api/sessions/{id}/script` to retrieve cached narration (stored in session).
- **Frontend**: PPT viewer gains a "播报" (narrate) button per slide that calls browser `SpeechSynthesis` to read the narration aloud.
- **Frontend**: Narration text displayed below each slide (collapsible).
- **Frontend**: Auto-advance option: after TTS finishes, optionally move to next slide.

## Capabilities

### New Capabilities
- `oral-script`: Per-slide oral narration generation (LLM) and TTS playback (browser SpeechSynthesis)

### Modified Capabilities
- `session-state`: Sessions now optionally store a `script` field (array of narration strings per slide)

## Impact

- **Backend**: `app/api/sessions.py` or new `app/api/script.py` — add script generation endpoint; `app/services/session_store.py` — add script storage; `app/services/script_gen.py` — LLM call to generate narrations
- **Frontend**: `PptViewerPage.tsx` — add narration display and TTS controls; `ChatPanel.tsx` — no change
- **Dependencies**: No new packages needed (browser SpeechSynthesis is native; LLM already wired)
- **DEV_MODE**: In DEV_MODE, script generation reads slide text from fixture PPTX and uses GLM to generate narrations (no special stub needed)
