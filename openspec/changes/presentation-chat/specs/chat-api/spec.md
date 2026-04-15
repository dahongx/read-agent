## ADDED Requirements

### Requirement: Chat endpoint accepts question and returns answer with sources
The system SHALL expose `POST /api/chat` accepting `{ session_id, question }` and returning `{ answer, sources }` where each source contains `text`, `file`, and `page`.

#### Scenario: Successful chat request
- **WHEN** client sends `POST /api/chat` with valid `session_id` and non-empty `question`
- **THEN** system returns HTTP 200 with `{ "answer": "<LLM response>", "sources": [{ "text": "...", "file": "...", "page": null }] }`

#### Scenario: Unknown session
- **WHEN** client sends `POST /api/chat` with an unknown `session_id`
- **THEN** system returns HTTP 404 with `{ "detail": "Session not found" }`

#### Scenario: Empty question rejected
- **WHEN** client sends `POST /api/chat` with an empty `question` string
- **THEN** system returns HTTP 422

#### Scenario: DEV_MODE uses fixture content as context
- **WHEN** `DEV_MODE=true` and chat request is received
- **THEN** system reads fixture `design_spec.md` (truncated to 4000 chars) as RAG context and passes it to LLM; sources contains one entry with `file: "design_spec.md"`

#### Scenario: LLM API error
- **WHEN** the Claude API call fails
- **THEN** system returns HTTP 502 with `{ "detail": "LLM error: <message>" }`
