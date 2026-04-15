## ADDED Requirements

### Requirement: Generate oral narrations for all slides
The system SHALL generate a text narration for each slide in the uploaded PPTX by calling the LLM with the slide's extracted text content. Narrations SHALL be cached in the session and returned on subsequent requests without re-generation.

#### Scenario: Generate narrations for a ready session
- **WHEN** client sends `POST /api/sessions/{id}/script`
- **THEN** system extracts text from each slide using python-pptx, calls LLM in parallel per slide, returns `{"script": ["narration1", "narration2", ...]}` with HTTP 200

#### Scenario: Return cached narrations
- **WHEN** client sends `GET /api/sessions/{id}/script` after narrations were already generated
- **THEN** system returns cached `{"script": [...]}` without calling LLM again

#### Scenario: Session not found
- **WHEN** client sends `POST /api/sessions/{id}/script` with unknown session id
- **THEN** system returns HTTP 404 with `{"detail": "Session not found"}`

#### Scenario: Slide has no text content
- **WHEN** a slide contains only images or shapes with no text
- **THEN** that slide's narration SHALL be a placeholder string (e.g., "此页为图表页，请参考幻灯片内容")

### Requirement: Play narration via browser TTS
The system SHALL provide TTS playback controls in the PPT viewer using the browser's `window.speechSynthesis` API.

#### Scenario: User clicks play on a slide with narration
- **WHEN** user clicks the "播报" button on a slide
- **THEN** browser speaks the narration text using `speechSynthesis.speak()`, button changes to "停止"

#### Scenario: User clicks stop during playback
- **WHEN** user clicks "停止" during TTS playback
- **THEN** browser calls `speechSynthesis.cancel()`, button returns to "播报"

#### Scenario: SpeechSynthesis not available
- **WHEN** the browser does not support `window.speechSynthesis`
- **THEN** TTS buttons SHALL be hidden; narration text is still displayed

### Requirement: Display narration text per slide
The system SHALL display the narration text for the current slide below the slide content in a collapsible panel.

#### Scenario: Narration panel collapsed by default
- **WHEN** the PPT viewer loads with narrations available
- **THEN** narration panel is collapsed showing only a toggle button "讲稿 ▼"

#### Scenario: User toggles narration panel
- **WHEN** user clicks "讲稿 ▼" toggle
- **THEN** narration text for current slide is shown; button changes to "讲稿 ▲"

#### Scenario: Navigating slides updates narration
- **WHEN** user navigates to a different slide
- **THEN** narration panel shows the narration for the new current slide
