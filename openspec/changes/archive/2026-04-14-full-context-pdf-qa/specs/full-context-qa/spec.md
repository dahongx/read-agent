## ADDED Requirements

### Requirement: Full-document context QA
The system SHALL send the complete paper text (all chunks sorted by page) as context to the LLM, instead of retrieving top-k chunks. If the total text exceeds 80,000 tokens, it SHALL fall back to top-16 RAG retrieval.

#### Scenario: Normal paper (fits in context window)
- **WHEN** user submits a question and the paper text is < 80K tokens
- **THEN** the full paper text (formatted with page markers) is sent as context to the LLM

#### Scenario: Oversized document fallback
- **WHEN** the total paper text estimate exceeds 80K tokens
- **THEN** the system falls back to retrieving top-16 RAG chunks

#### Scenario: No RAG index available
- **WHEN** session has no `rag_index_path` (e.g., DEV_MODE_RAG=true)
- **THEN** system uses the existing DEV_MODE fixture context (design_spec.md)

### Requirement: Inline page citations in LLM answers
The system prompt SHALL instruct the LLM to cite page numbers inline using the format `(第N页)`. The backend SHALL parse these references from the answer and return them as the sources list.

#### Scenario: LLM cites pages in answer
- **WHEN** LLM responds with text containing one or more `(第N页)` references
- **THEN** backend parses these into `Source` objects with `page=N`, `text` = surrounding sentence, `file` = PDF filename
- **THEN** response `sources` list contains these parsed references

#### Scenario: LLM provides no page citations
- **WHEN** LLM answer contains no `(第N页)` references
- **THEN** `sources` list is empty (no fabricated sources)
