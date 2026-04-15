## ADDED Requirements

### Requirement: Render inline page citation badges in chat
The frontend SHALL parse `(第N页)` patterns in assistant answer text and render them as clickable blue badges. Clicking a badge SHALL open the PDF viewer modal at that page.

#### Scenario: Answer contains page citation
- **WHEN** assistant answer text contains `(第3页)`
- **THEN** it is rendered as a clickable blue badge `[第3页]` inline in the text
- **WHEN** user clicks the badge
- **THEN** PDF viewer modal opens showing the PDF at page 3

#### Scenario: Answer contains no citations
- **WHEN** assistant answer text has no `(第N页)` patterns
- **THEN** text is rendered as plain text, no badges shown

### Requirement: Embedded PDF viewer modal
The system SHALL display the uploaded PDF in an iframe modal when a citation badge is clicked. The iframe URL SHALL include a `#page=N` fragment to position the PDF at the cited page.

#### Scenario: Open PDF viewer at specific page
- **WHEN** user clicks a citation badge for page N
- **THEN** a modal overlay appears (80% viewport width/height) containing an iframe
- **THEN** the iframe src is `/api/sessions/{id}/pdf#page=N`
- **THEN** the PDF is rendered by the browser's built-in PDF viewer at page N

#### Scenario: Close PDF viewer
- **WHEN** user clicks the "×" close button or clicks outside the modal
- **THEN** modal dismisses and chat panel is fully visible again
