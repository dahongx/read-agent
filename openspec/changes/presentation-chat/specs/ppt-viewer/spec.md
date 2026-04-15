## MODIFIED Requirements

### Requirement: PPTX rendering in browser
The system SHALL render the generated PPTX file as slides in the left panel of the presentation page (not full-screen), with previous/next navigation controls and a download button. The panel SHALL occupy approximately 60% of the page width on screens wider than 768px.

#### Scenario: PPT loads in left panel
- **WHEN** the user navigates to `/session/{session_id}/ppt`
- **THEN** the system fetches the PPTX file from `GET /api/sessions/{session_id}/ppt`, renders the first slide in the left panel, and displays the total slide count

#### Scenario: Navigate to next slide
- **WHEN** user clicks the "Next" button or presses the right arrow key
- **THEN** the next slide is displayed and the slide counter updates (e.g., "2 / 12")

#### Scenario: Navigate to previous slide
- **WHEN** user clicks the "Prev" button or presses the left arrow key and current slide is not the first
- **THEN** the previous slide is displayed and the slide counter updates

#### Scenario: At first slide, Prev is disabled
- **WHEN** the current slide is the first slide
- **THEN** the "Prev" button is visually disabled and clicking it has no effect

#### Scenario: At last slide, Next is disabled
- **WHEN** the current slide is the last slide
- **THEN** the "Next" button is visually disabled and clicking it has no effect

#### Scenario: PPTX render fallback
- **WHEN** pptxjs fails to render the PPTX file
- **THEN** the system displays a "Preview unavailable" message and a download button for the original PPTX file

### Requirement: PPTX download
The system SHALL provide a download button that lets the user save the generated PPTX file.

#### Scenario: Download button clicked
- **WHEN** user clicks "Download PPT"
- **THEN** the browser downloads the PPTX file from `GET /api/sessions/{session_id}/ppt`
