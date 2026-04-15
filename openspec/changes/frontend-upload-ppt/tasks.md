## 1. Project Setup

- [x] 1.1 Scaffold Vite + React 18 + TypeScript project in `frontend/` (`npm create vite@latest frontend -- --template react-ts`)
- [x] 1.2 Install dependencies: `react-router-dom`, `tailwindcss`, `postcss`, `autoprefixer`
- [x] 1.3 Configure Tailwind CSS (`tailwind.config.js`, add directives to `index.css`)
- [x] 1.4 Configure Vite dev proxy: forward `/api` and `/ws` to `http://localhost:8000`

## 2. Backend: PPT File Download Route

- [x] 2.1 Add `GET /api/sessions/{session_id}/ppt` route to `backend/app/api/sessions.py` — serve the PPTX file as a file response (use `FileResponse`); return 404 if not ready

## 3. Routing & Layout

- [x] 3.1 Set up React Router v6 in `frontend/src/main.tsx` with three routes: `/`, `/session/:id`, `/session/:id/ppt`
- [x] 3.2 Create a minimal shared `Layout` component with a top header bar

## 4. Upload Page (`/`)

- [x] 4.1 Create `UploadPage` component with drag-and-drop zone and click-to-browse input (accept=".pdf")
- [x] 4.2 Client-side PDF validation: show inline error if non-PDF selected
- [x] 4.3 Call `POST /api/upload` on file selection; show spinner while in-flight; navigate to `/session/{id}` on success
- [x] 4.4 Display API error message inline on failure

## 5. WebSocket Hook

- [x] 5.1 Create `useWebSocket(sessionId)` custom hook: connects to `/ws/{sessionId}`, returns `{ lastMessage, readyState }`
- [x] 5.2 Add auto-reconnect logic: on unexpected close, retry every 3 seconds with a "Connection lost — retrying…" indicator

## 6. Progress Page (`/session/:id`)

- [x] 6.1 Create `ProgressPage` component; connect `useWebSocket` on mount
- [x] 6.2 Render two progress bars: PPT generation and RAG indexing, with step label and percentage
- [x] 6.3 Handle `done` event: show success state, navigate to `/session/:id/ppt` after 1 second
- [x] 6.4 Handle `error` event: show error banner and "Go back" button

## 7. PPT Viewer Page (`/session/:id/ppt`)

- [x] 7.1 Fetch PPTX binary from `GET /api/sessions/{id}/ppt` on mount
- [x] 7.2 Render PPTX using `pptxjs` (or fallback: show download button + "Preview unavailable" if render fails)
- [x] 7.3 Add Prev / Next navigation buttons with keyboard arrow key support
- [x] 7.4 Show slide counter (e.g., "2 / 12"); disable Prev on first slide, Next on last slide
- [x] 7.5 Add "Download PPT" button that triggers file download
