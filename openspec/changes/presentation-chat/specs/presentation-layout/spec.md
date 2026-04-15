## ADDED Requirements

### Requirement: Left-right split layout on presentation page
The system SHALL display the PPT viewer and chat panel side by side on `/session/:id/ppt`, with the PPT occupying ~60% width and the chat panel ~40% width.

#### Scenario: Layout renders correctly on wide screen
- **WHEN** user navigates to `/session/:id/ppt` on a screen wider than 768px
- **THEN** PPT panel and chat panel appear side by side in a 3:2 ratio

#### Scenario: Layout stacks on narrow screen
- **WHEN** user views the page on a screen narrower than 768px
- **THEN** PPT panel appears above and chat panel appears below

### Requirement: Chat panel shows conversation history
The system SHALL display the full conversation history in the chat panel, with user messages and assistant answers visually distinguished. Each assistant message SHALL show collapsible source references below it.

#### Scenario: User submits a question
- **WHEN** user types a question and presses Enter or clicks Send
- **THEN** the question appears as a user message, a loading indicator shows, and the assistant answer appears when the API responds

#### Scenario: Sources shown under answer
- **WHEN** an assistant answer includes sources
- **THEN** a "查看引用" toggle appears below the answer; clicking it reveals source cards with the original text snippet and file name

#### Scenario: Send button disabled while loading
- **WHEN** a chat request is in flight
- **THEN** the input field and Send button are disabled until the response arrives
