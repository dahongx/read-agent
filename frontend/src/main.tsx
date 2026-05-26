import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import Layout from './components/Layout'
import UploadPage from './pages/UploadPage'
import ProgressPage from './pages/ProgressPage'
import PptViewerPage from './pages/PptViewerPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<UploadPage />} />
          <Route path="/tasks/:id" element={<ProgressPage />} />
          <Route path="/space/:spaceId" element={<PptViewerPage />} />
          {/* 旧 URL 重定向 */}
          <Route path="/session/:id" element={<ProgressPage />} />
          <Route path="/session/:id/ppt" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
