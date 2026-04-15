## Why

PRD Feature 5 requires voice-based interaction with the literature database. Currently users can only type questions. This change adds a microphone button to the chat panel so users can ask questions by voice (browser Speech Recognition), hear the LLM answer read aloud (browser TTS), and click source links to jump to the relevant page in the PDF viewer.

## What Changes

- **Frontend**: ChatPanel gains a microphone button — clicking it starts browser `SpeechRecognition`; recognized text is auto-filled into the input and submitted.
- **Frontend**: After receiving an LLM answer, optionally auto-play the answer text via `speechSynthesis` (with a toggle to enable/disable auto-play).
- **Frontend**: Source cards in chat gain a "跳转到页面" button that communicates the page number to the PPT viewer, scrolling/jumping to that slide.
- **Backend**: No new endpoints needed; voice input uses browser-native APIs; `/api/chat` endpoint is unchanged.

## Capabilities

### New Capabilities
- `voice-qa`: Voice input (browser SpeechRecognition) and TTS answer playback for chat Q&A

### Modified Capabilities
- (none — `/api/chat` endpoint behavior unchanged)

## Impact

- **Frontend only**: `ChatPanel.tsx` — add voice input button and TTS playback; `PptViewerPage.tsx` — handle slide jump signal from ChatPanel when user clicks source link
- **Dependencies**: No new packages; browser Web Speech API (SpeechRecognition + SpeechSynthesis) is native
- **Browser support**: Chrome/Edge fully support SpeechRecognition; Firefox has limited support — graceful degradation required
