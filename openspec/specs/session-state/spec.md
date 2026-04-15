## ADDED Requirements

### Requirement: Store and retrieve session state in memory
The system SHALL maintain an in-memory dictionary of sessions keyed by session_id. Each session SHALL store: status, progress (ppt + rag), error message (optional), and file paths of outputs.

#### Scenario: Create new session
- **WHEN** a PDF is successfully uploaded
- **THEN** a new SessionState object is created with `status="pending"` and stored in the session dict

#### Scenario: Query existing session
- **WHEN** client sends GET `/api/sessions/{session_id}`
- **THEN** system returns the current SessionState as JSON, including status, progress, and any output paths

#### Scenario: Query non-existent session
- **WHEN** client sends GET `/api/sessions/{session_id}` with an unknown ID
- **THEN** system returns HTTP 404 with `{"detail": "Session not found"}`

### Requirement: Session state transitions
The system SHALL enforce valid session status transitions: `pending` → `processing` → `ready` | `error`. Invalid transitions SHALL raise an internal error.

#### Scenario: Valid status transition
- **WHEN** task_manager calls `update_status(session_id, "processing")`
- **THEN** session status is updated and all WebSocket subscribers are notified

#### Scenario: Session status is never downgraded
- **WHEN** a task attempts to set status to `pending` on a session already in `processing`
- **THEN** the system raises an internal ValueError and logs the attempted invalid transition
