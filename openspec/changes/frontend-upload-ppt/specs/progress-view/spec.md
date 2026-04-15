## ADDED Requirements

### Requirement: Real-time dual progress bars via WebSocket
The system SHALL display two independent progress bars—one for PPT generation and one for RAG index building—updated in real time via a WebSocket connection to `/ws/{session_id}`.

#### Scenario: WebSocket connection on page load
- **WHEN** the progress page mounts with a valid session_id
- **THEN** a WebSocket connection is established to `/ws/{session_id}` and the current session state is displayed immediately from the first snapshot message

#### Scenario: Progress bar updates live
- **WHEN** a `{"event": "progress", "task": "ppt", "step": "...", "pct": N}` message is received
- **THEN** the PPT progress bar advances to N% and the step label updates

#### Scenario: Both tasks complete
- **WHEN** a `{"event": "done", "status": "ready"}` message is received
- **THEN** both progress bars show 100%, a success message is displayed, and the UI navigates to `/session/{session_id}/ppt` after a 1-second delay

#### Scenario: Task error displayed
- **WHEN** a `{"event": "error", "message": "..."}` message is received
- **THEN** an error banner is displayed with the message and a "Go back" button to return to the upload page

#### Scenario: WebSocket disconnected
- **WHEN** the WebSocket connection drops unexpectedly
- **THEN** the UI displays a "Connection lost — retrying…" indicator and attempts to reconnect every 3 seconds

### Requirement: Session state recovery on refresh
The system SHALL recover the current session state when the progress page is loaded or refreshed, so users do not lose progress visibility.

#### Scenario: Page refreshed while tasks are running
- **WHEN** user refreshes the progress page
- **THEN** the WebSocket reconnects and the first snapshot message restores both progress bars to their last known state
