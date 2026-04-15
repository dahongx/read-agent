## ADDED Requirements

### Requirement: Launch parallel async tasks after PDF upload
The system SHALL launch two independent async tasks concurrently after a PDF is uploaded: PPT generation and RAG index building. Both tasks SHALL run in parallel without waiting for each other.

#### Scenario: Both tasks start after upload
- **WHEN** a valid PDF is uploaded and session is created
- **THEN** task_manager launches ppt_task and rag_task concurrently via asyncio.create_task, and session status transitions to `processing`

#### Scenario: Both tasks complete successfully
- **WHEN** both ppt_task and rag_task complete without error
- **THEN** session status transitions to `ready`

#### Scenario: One task fails
- **WHEN** either ppt_task or rag_task raises an exception
- **THEN** session status transitions to `error` and the error message is stored in the session

### Requirement: Report task progress
The system SHALL update session progress state as each task proceeds, so that progress queries and WebSocket clients receive live updates.

#### Scenario: PPT task reports progress
- **WHEN** ppt_task emits a progress event (step name + percentage)
- **THEN** session.progress.ppt is updated and a WebSocket message is broadcast to all subscribers of this session

#### Scenario: RAG task reports progress
- **WHEN** rag_task emits a progress event (step name + percentage)
- **THEN** session.progress.rag is updated and a WebSocket message is broadcast to all subscribers of this session
