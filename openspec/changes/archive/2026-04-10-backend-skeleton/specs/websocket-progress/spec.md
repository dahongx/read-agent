## ADDED Requirements

### Requirement: WebSocket endpoint for live progress
The system SHALL expose a WebSocket endpoint at `/ws/{session_id}`. Clients connect to receive JSON progress messages pushed by the server as tasks advance.

#### Scenario: Client connects to valid session
- **WHEN** client opens WebSocket to `/ws/{session_id}` and session exists
- **THEN** server accepts the connection, adds it to the subscriber list for that session, and immediately sends the current session state as the first message

#### Scenario: Client connects to unknown session
- **WHEN** client opens WebSocket to `/ws/{session_id}` and session does not exist
- **THEN** server sends `{"error": "session not found"}` and closes the connection

#### Scenario: Progress event broadcast
- **WHEN** task_manager emits a progress update for a session
- **THEN** server pushes `{"event": "progress", "task": "<ppt|rag>", "step": "<name>", "pct": <0-100>}` to all connected WebSocket clients for that session

#### Scenario: Task completion broadcast
- **WHEN** both tasks complete and session transitions to `ready`
- **THEN** server pushes `{"event": "done", "status": "ready"}` to all connected clients

#### Scenario: Client disconnects gracefully
- **WHEN** client closes the WebSocket connection
- **THEN** server removes the client from the subscriber list without error; remaining clients are unaffected

### Requirement: Connection manager
The system SHALL maintain a ConnectionManager that maps session_id to a list of active WebSocket connections, supporting concurrent multi-client subscriptions to the same session.

#### Scenario: Multiple clients on same session
- **WHEN** two clients connect to the same `/ws/{session_id}`
- **THEN** both receive all subsequent progress messages for that session
