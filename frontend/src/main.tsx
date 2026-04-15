import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
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
          <Route path="/session/:id" element={<ProgressPage />} />
          <Route path="/session/:id/ppt" element={<PptViewerPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
