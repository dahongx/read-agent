## 1. Backend: Dependencies & Config

- [x] 1.1 Add `anthropic>=0.28.0` to `backend/requirements.txt` and install it
- [x] 1.2 Add `ANTHROPIC_API_KEY=` to `backend/.env.example`
- [x] 1.3 Add `ANTHROPIC_API_KEY: str = ""` field to `backend/app/core/config.py` Settings

## 2. Backend: RAG Service (stub + DEV_MODE)

- [x] 2.1 Create `backend/app/services/rag.py` — `retrieve(session_id, question) -> list[dict]`: DEV_MODE reads fixture `design_spec.md` (first 4000 chars) and returns one source entry; real mode returns empty list

## 3. Backend: Chat API

- [x] 3.1 Create `backend/app/api/chat.py` — `POST /api/chat` with request body `{ session_id, question }`: calls `rag.retrieve`, builds system prompt with context, calls Claude claude-haiku-4-5-20251001, returns `{ answer, sources }`
- [x] 3.2 Register chat router in `backend/main.py`

## 4. Frontend: Chat Panel Component

- [x] 4.1 Create `frontend/src/components/ChatPanel.tsx` — message list (user/assistant bubbles), input box, Send button, loading state
- [x] 4.2 Add collapsible source cards under each assistant message (toggle "查看引用")
- [x] 4.3 Implement `POST /api/chat` call on submit; disable input while loading; append response to message list

## 5. Frontend: Presentation Layout

- [x] 5.1 Refactor `frontend/src/pages/PptViewerPage.tsx` into left-right grid layout (`grid-cols-1 md:grid-cols-[3fr_2fr]`)
- [x] 5.2 Move PPT rendering + controls into left panel; mount `<ChatPanel sessionId={id} />` in right panel
