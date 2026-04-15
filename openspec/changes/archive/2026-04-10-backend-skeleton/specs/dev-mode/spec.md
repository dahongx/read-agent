## ADDED Requirements

### Requirement: DEV_MODE skips PPT generation and reuses fixture
When `DEV_MODE=true` is set in the environment, the system SHALL skip the actual PPT generation task and instead load the pre-validated fixture from `projects/M_plus_MemoryLLM_ppt169_20260409/`.

#### Scenario: DEV_MODE enabled with complete fixture
- **WHEN** `DEV_MODE=true` and the fixture directory contains all required files (`.pptx`, `design_spec.md`, `notes/`)
- **THEN** ppt_task immediately returns fixture paths without executing actual PPT generation, and logs "DEV_MODE: using fixture"

#### Scenario: DEV_MODE enabled with incomplete fixture
- **WHEN** `DEV_MODE=true` but one or more required fixture files are missing
- **THEN** system raises a `FixtureIncompleteError` with a clear message listing which files are missing; it SHALL NOT silently fall back to any other behavior

#### Scenario: DEV_MODE disabled
- **WHEN** `DEV_MODE` is unset or `DEV_MODE=false`
- **THEN** system runs the actual PPT generation task normally; fixture directory is never accessed

### Requirement: Fixture completeness validation at startup
The system SHALL validate fixture completeness when `DEV_MODE=true` is detected at application startup, so that missing fixtures are caught before the first request arrives.

#### Scenario: Startup with DEV_MODE and missing fixture
- **WHEN** application starts with `DEV_MODE=true` and fixture is incomplete
- **THEN** application startup FAILS with a descriptive error message listing missing files; it SHALL NOT start serving requests
