## 1. Frontend: Lift Slide Navigation Prop

- [x] 1.1 In `PptViewerPage.tsx`, add `onJumpToSlide` callback prop to `ChatPanel` component call — pass a function `(page: number) => setCurrent(Math.min(page - 1, slides.length - 1))`
- [x] 1.2 In `ChatPanel.tsx`, add `onJumpToSlide?: (page: number) => void` to the `Props` interface

## 2. Frontend: Source Card Jump Button

- [x] 2.1 In `SourceCard` component in `ChatPanel.tsx`, add `onJump?: () => void` prop
- [x] 2.2 When `source.page != null && onJump`, render a "跳转" button that calls `onJump()`
- [x] 2.3 Pass `onJump` from `AssistantMessage` down to `SourceCard` (thread `onJumpToSlide` through `AssistantMessage` → `SourceCard`)

## 3. Frontend: Voice Input (SpeechRecognition)

- [x] 3.1 In `ChatPanel.tsx`, detect SpeechRecognition support on mount: `const SR = window.SpeechRecognition || (window as any).webkitSpeechRecognition`
- [x] 3.2 Add `listening` state (boolean) to ChatPanel
- [x] 3.3 Add microphone button next to send button — only render if `SR` is available
- [x] 3.4 On microphone button click: create `SpeechRecognition` instance with `lang="zh-CN"`, `interimResults=false`, `maxAlternatives=1`; start it; set `listening=true`
- [x] 3.5 On `recognition.onresult`: extract transcript, set input value, call `send()`, set `listening=false`
- [x] 3.6 On `recognition.onerror`: if error is `not-allowed`, show inline error message "麦克风权限被拒绝"; set `listening=false`
- [x] 3.7 On `recognition.onend`: set `listening=false` (handles timeout / no speech)
- [x] 3.8 Add TypeScript type declaration for `webkitSpeechRecognition` on `window` to avoid TS errors

## 4. Frontend: TTS Playback Toggle

- [x] 4.1 Add `ttsEnabled` state (boolean, default false) to ChatPanel
- [x] 4.2 Detect `window.speechSynthesis` support; only show toggle if supported
- [x] 4.3 Add speaker toggle button in ChatPanel header (🔇/🔊 or text "朗读" toggle)
- [x] 4.4 In `send()` function's success handler: if `ttsEnabled && speechSynthesis available`, cancel any current utterance and speak the answer text
- [x] 4.5 Handle `speechSynthesis.cancel()` before starting new utterance to prevent overlap
