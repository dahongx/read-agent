## ADDED Requirements

### Requirement: Accept PDF upload and create session
The system SHALL accept a multipart/form-data POST request to `/api/upload` containing a PDF file, validate the file format, create a new session, and return the session_id.

#### Scenario: Valid PDF upload
- **WHEN** client sends POST `/api/upload` with a valid `.pdf` file
- **THEN** system creates a new session with status `pending`, saves the file to a temp directory, and returns `{"session_id": "<uuid>", "status": "pending"}`

#### Scenario: Non-PDF file rejected
- **WHEN** client sends POST `/api/upload` with a non-PDF file (e.g., `.docx`)
- **THEN** system returns HTTP 400 with `{"detail": "Only PDF files are accepted"}`

#### Scenario: Empty file rejected
- **WHEN** client sends POST `/api/upload` with an empty file (0 bytes)
- **THEN** system returns HTTP 400 with `{"detail": "Uploaded file is empty"}`
