## ADDED Requirements

### Requirement: Voice input via microphone
The system SHALL provide a microphone button in the chat panel that starts browser SpeechRecognition when clicked. Recognized speech SHALL be placed into the text input and auto-submitted as a question.

#### Scenario: User clicks microphone button (supported browser)
- **WHEN** user clicks the microphone button in a supported browser (Chrome/Edge)
- **THEN** browser requests microphone permission, starts SpeechRecognition with lang="zh-CN", button shows "录音中..." state

#### Scenario: Speech recognized
- **WHEN** SpeechRecognition fires `onresult` with a transcript
- **THEN** the transcript text is placed in the chat input and submitted automatically

#### Scenario: SpeechRecognition not supported
- **WHEN** the browser does not support `window.SpeechRecognition` and `window.webkitSpeechRecognition`
- **THEN** the microphone button SHALL be hidden entirely

#### Scenario: Microphone permission denied
- **WHEN** user denies microphone permission
- **THEN** system shows an inline error: "麦克风权限被拒绝，请检查浏览器设置"

### Requirement: TTS playback of assistant answers
The system SHALL provide an opt-in TTS toggle in the chat panel header. When enabled, each new assistant answer SHALL be read aloud via browser SpeechSynthesis.

#### Scenario: TTS toggle OFF (default)
- **WHEN** chat panel loads
- **THEN** TTS toggle is OFF; no automatic TTS playback occurs

#### Scenario: User enables TTS toggle
- **WHEN** user clicks the TTS speaker toggle to enable it
- **THEN** the next received assistant answer is automatically read aloud via speechSynthesis

#### Scenario: New answer arrives while TTS is playing
- **WHEN** a new assistant answer arrives while a previous TTS utterance is still playing
- **THEN** the previous utterance is cancelled and the new answer begins playing

#### Scenario: SpeechSynthesis not available
- **WHEN** browser does not support `window.speechSynthesis`
- **THEN** TTS toggle SHALL be hidden; no TTS functionality is shown

### Requirement: Jump to source page in PPT viewer
The system SHALL add a jump button to source cards in the chat panel that navigates the PPT viewer to the approximate slide corresponding to the source page number.

#### Scenario: User clicks jump button on source card
- **WHEN** user clicks "跳转" on a source card with a page number
- **THEN** the PPT viewer navigates to `min(page - 1, slides.length - 1)` slide index (0-based)

#### Scenario: Source card has no page number
- **WHEN** a source card has `page: null`
- **THEN** the jump button SHALL not be shown for that source card
