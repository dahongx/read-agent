## ADDED Requirements

### Requirement: PDF file selection and upload
The system SHALL provide an upload area that accepts PDF files via drag-and-drop or click-to-browse, calls `POST /api/upload`, and navigates to the progress page on success.

#### Scenario: Successful drag-and-drop upload
- **WHEN** user drags a PDF file onto the upload area and releases
- **THEN** the file is submitted to `POST /api/upload` and the UI navigates to `/session/{session_id}`

#### Scenario: Successful click-to-browse upload
- **WHEN** user clicks the upload area and selects a PDF file from the file picker
- **THEN** the file is submitted to `POST /api/upload` and the UI navigates to `/session/{session_id}`

#### Scenario: Non-PDF file rejected on client side
- **WHEN** user drags or selects a non-PDF file
- **THEN** the system displays an inline error "Please select a PDF file" and does NOT call the API

#### Scenario: Upload in progress state
- **WHEN** the file has been submitted and the API call is in flight
- **THEN** the upload button is disabled and a loading spinner is shown

#### Scenario: API error displayed
- **WHEN** the `POST /api/upload` call returns an error (4xx or 5xx)
- **THEN** the error message from the API response is displayed inline and the user can retry
