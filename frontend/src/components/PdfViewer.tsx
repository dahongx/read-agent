import { useEffect, useRef } from 'react'

interface Props {
  pdfUrl: string
  page: number
  fileLabel?: string | null
  quote?: string | null
  onClose: () => void
}

export default function PdfViewer({ pdfUrl, page, fileLabel, quote, onClose }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const encodedUrl = encodeURIComponent(pdfUrl)
  // PDF.js viewer 使用 hash 参数控制：page=N 跳页；search=...&phrase=true 在加载完毕后做短语高亮
  const hashParts = [`page=${page}`]
  if (quote && quote.trim()) {
    hashParts.push(`search=${encodeURIComponent(quote.trim())}`)
    hashParts.push('phrase=true')
    hashParts.push('highlightAll=true')
  }
  const src = `/pdfjs/viewer.html?file=${encodedUrl}#${hashParts.join('&')}`
  const title = fileLabel ? `${fileLabel} · 第 ${page} 页` : `第 ${page} 页 · 原文`
  const subtitle = quote ? `高亮：${quote.length > 60 ? quote.slice(0, 60) + '…' : quote}` : null

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
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-medium text-gray-700">{title}</span>
            {subtitle && (
              <span className="text-xs text-amber-600 truncate" title={quote ?? ''}>{subtitle}</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-2xl font-light leading-none px-1"
          >×</button>
        </div>
        <iframe
          ref={iframeRef}
          key={`${pdfUrl}-${page}-${quote ?? ''}`}
          src={src}
          className="flex-1 w-full rounded-b-lg border-0"
          title="PDF 查看器"
        />
      </div>
    </div>
  )
}
