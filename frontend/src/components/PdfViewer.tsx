import { useEffect, useRef } from 'react'

interface Props {
  sessionId: string
  page: number
  onClose: () => void
}

export default function PdfViewer({ sessionId, page, onClose }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const pdfUrl = encodeURIComponent(`/api/sessions/${sessionId}/pdf`)
  const src = `/pdfjs/viewer.html?file=${pdfUrl}&page=${page}`

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
          <span className="text-sm font-medium text-gray-700">第 {page} 页 · 原文</span>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-2xl font-light leading-none px-1"
          >×</button>
        </div>
        <iframe
          ref={iframeRef}
          key={`${sessionId}-${page}`}
          src={src}
          className="flex-1 w-full rounded-b-lg border-0"
          title="PDF 查看器"
        />
      </div>
    </div>
  )
}
