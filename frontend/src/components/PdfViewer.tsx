import { useEffect, useRef } from 'react'

interface Props {
  sessionId: string
  page: number
  docId?: string | null
  fileLabel?: string | null
  onClose: () => void
}

export default function PdfViewer({ sessionId, page, docId, fileLabel, onClose }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const pdfPath = docId
    ? `/api/sessions/${sessionId}/pdf/${encodeURIComponent(docId)}`
    : `/api/sessions/${sessionId}/pdf`
  const pdfUrl = encodeURIComponent(pdfPath)
  const src = `/pdfjs/viewer.html?file=${pdfUrl}&page=${page}`
  const title = fileLabel ? `${fileLabel} · 第 ${page} 页` : `第 ${page} 页 · 原文`

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-2xl flex flex-col"
        style={{ width: '82vw', height: '90vh' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 shrink-0">
          <span className="text-sm font-medium text-gray-700">{title}</span>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-2xl font-light leading-none px-1"
          >×</button>
        </div>
        <iframe
          ref={iframeRef}
          key={`${sessionId}-${docId ?? 'session'}-${page}`}
          src={src}
          className="flex-1 w-full rounded-b-lg border-0"
          title="PDF 查看器"
        />
      </div>
    </div>
  )
}
