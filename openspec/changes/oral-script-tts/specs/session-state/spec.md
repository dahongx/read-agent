## ADDED Requirements

### Requirement: Session stores optional oral script
The system SHALL add an optional `script` field to SessionData that stores a list of narration strings (one per slide). This field SHALL default to `None` and be populated only after `/api/sessions/{id}/script` is called.

#### Scenario: Script field absent on new session
- **WHEN** a new session is created after PDF upload
- **THEN** `GET /api/sessions/{id}` response does not include a `script` field (or includes it as null)

#### Scenario: Script field present after generation
- **WHEN** `POST /api/sessions/{id}/script` completes successfully
- **THEN** `GET /api/sessions/{id}` response includes `script` as an array of strings
