import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import ChatPanel from '../components/ChatPanel'
import { preprocessForTts } from '../utils/tts'

export default function PptViewerPage() {
  const { id } = useParams<{ id: string }>()
  const [slides, setSlides] = useState<string[]>([])
  const [current, setCurrent] = useState(0)
  const [loading, setLoading] = useState(true)
  const [noSlides, setNoSlides] = useState(false)

  // Narration
  const [script, setScript] = useState<string[]>([])
  const [scriptLoading, setScriptLoading] = useState(false)
  const [scriptOpen, setScriptOpen] = useState(false)

  // TTS / auto-play — fix 1 & 4
  const ttsSupported = typeof window !== 'undefined' && 'speechSynthesis' in window
  const [autoPlaying, setAutoPlaying] = useState(false)
  const autoPlayingRef = useRef(false)
  const currentRef = useRef(0)
  const scriptRef = useRef<string[]>([])
  const slidesRef = useRef<string[]>([])

  currentRef.current = current
  scriptRef.current = script
  slidesRef.current = slides

  const downloadUrl = `/api/sessions/${id}/ppt`

  useEffect(() => {
    async function loadSlides() {
      try {
        const res = await fetch(`/api/sessions/${id}/slides`)
        if (!res.ok) throw new Error()
        const data = await res.json()
        if (data.slides?.length > 0) {
          setSlides(data.slides)
        } else {
          setNoSlides(true)
        }
      } catch {
        setNoSlides(true)
      } finally {
        setLoading(false)
      }
    }
    loadSlides()
  }, [id])

  useEffect(() => {
    if (loading || noSlides || slides.length === 0) return
    async function fetchScript() {
      setScriptLoading(true)
      try {
        const res = await fetch(`/api/sessions/${id}/script`, { method: 'POST' })
        if (res.ok) setScript((await res.json()).script ?? [])
      } catch { /* silent */ }
      finally { setScriptLoading(false) }
    }
    fetchScript()
  }, [id, loading, noSlides, slides.length])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'ArrowRight') setCurrent(c => Math.min(c + 1, slides.length - 1))
      if (e.key === 'ArrowLeft') setCurrent(c => Math.max(c - 1, 0))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [slides.length])

  // Fix 1: auto-advance — speak slide, on end advance
  function speakSlideAt(index: number) {
    if (!autoPlayingRef.current || !ttsSupported) return
    const narration = scriptRef.current[index]
    window.speechSynthesis.cancel()
    if (!narration) {
      // skip empty, advance
      const next = index + 1
      if (next < slidesRef.current.length) {
        setCurrent(next)
        setTimeout(() => speakSlideAt(next), 100)
      } else {
        stopAutoPlay()
      }
      return
    }
    const utterance = new SpeechSynthesisUtterance(preprocessForTts(narration))
    utterance.lang = 'zh-CN'
    utterance.onend = () => {
      if (!autoPlayingRef.current) return
      const next = currentRef.current + 1
      if (next < slidesRef.current.length) {
        setCurrent(next)
        setTimeout(() => speakSlideAt(next), 300)
      } else {
        stopAutoPlay()
      }
    }
    utterance.onerror = () => stopAutoPlay()
    window.speechSynthesis.speak(utterance)
  }

  function startAutoPlay() {
    if (!ttsSupported) return
    autoPlayingRef.current = true
    setAutoPlaying(true)
    speakSlideAt(currentRef.current)
  }

  function stopAutoPlay() {
    autoPlayingRef.current = false
    setAutoPlaying(false)
    window.speechSynthesis.cancel()
  }

  // Stop auto-play when user manually changes slide
  function goToSlide(index: number) {
    if (autoPlaying) stopAutoPlay()
    setCurrent(index)
  }

  const slideUrl = slides.length > 0
    ? `/api/sessions/${id}/slides/${encodeURIComponent(slides[current])}`
    : ''
  const currentNarration = script[current] ?? ''

  return (
    <div className="grid grid-cols-1 md:grid-cols-[3fr_2fr] overflow-hidden" style={{ height: 'calc(100vh - 57px)', minHeight: 0 }}>
      <div className="flex flex-col min-h-0 overflow-hidden border-r border-gray-200 bg-white">
        {loading ? (
          <div className="flex flex-col items-center justify-center flex-1 gap-3 text-gray-500">
            <svg className="animate-spin h-8 w-8" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span>加载幻灯片...</span>
          </div>
        ) : noSlides ? (
          <div className="flex flex-col items-center justify-center flex-1 gap-4 p-8 text-center">
            <p className="text-gray-500 text-sm">幻灯片预览暂不可用</p>
            <a href={downloadUrl} download className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">下载 PPT</a>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-hidden flex items-center justify-center bg-gray-100 p-2">
              <img
                key={slideUrl}
                src={slideUrl}
                alt={`幻灯片 ${current + 1}`}
                className="max-w-full max-h-full object-contain shadow-md rounded"
              />
            </div>

            {/* Narration panel */}
            {(script.length > 0 || scriptLoading) && (
              <div className="border-t border-gray-200 bg-gray-50">
                <button
                  onClick={() => setScriptOpen(o => !o)}
                  className="w-full flex items-center justify-between px-4 py-2 text-xs text-gray-500 hover:bg-gray-100"
                >
                  <span className="font-medium">讲稿</span>
                  <span>{scriptLoading ? '加载讲稿中...' : scriptOpen ? '▲' : '▼'}</span>
                </button>
                {scriptOpen && !scriptLoading && currentNarration && (
                  <div className="px-4 pb-3 text-sm text-gray-700 leading-relaxed max-h-40 overflow-y-auto">
                    {currentNarration}
                  </div>
                )}
              </div>
            )}

            {/* Controls */}
            <div className="flex items-center justify-center gap-2 px-4 py-3 border-t border-gray-200 bg-gray-50 flex-wrap">
              <button onClick={() => goToSlide(Math.max(current - 1, 0))} disabled={current === 0}
                className="px-3 py-1.5 rounded border border-gray-300 text-gray-700 text-sm disabled:opacity-40 hover:bg-gray-100">
                ← 上一页
              </button>
              <span className="text-sm text-gray-500 w-16 text-center">{current + 1} / {slides.length}</span>
              <button onClick={() => goToSlide(Math.min(current + 1, slides.length - 1))} disabled={current === slides.length - 1}
                className="px-3 py-1.5 rounded border border-gray-300 text-gray-700 text-sm disabled:opacity-40 hover:bg-gray-100">
                下一页 →
              </button>

              {/* Fix 1: auto-play button */}
              {ttsSupported && script.length > 0 && (
                autoPlaying ? (
                  <button onClick={stopAutoPlay}
                    className="px-3 py-1.5 rounded border border-red-300 text-red-600 hover:bg-red-50 text-sm animate-pulse">
                    ⏹ 停止播报
                  </button>
                ) : (
                  <button onClick={startAutoPlay} disabled={scriptLoading}
                    className="px-3 py-1.5 rounded border border-blue-300 text-blue-600 hover:bg-blue-50 text-sm disabled:opacity-40">
                    ▶ 连续播报
                  </button>
                )
              )}

              <a href={downloadUrl} download className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">下载</a>
            </div>
          </>
        )}
      </div>

      <ChatPanel
        sessionId={id!}
        onJumpToSlide={(page) => goToSlide(Math.min(page - 1, slides.length - 1))}
      />
    </div>
  )
}
