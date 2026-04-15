import React, { useState, useRef, useEffect, type KeyboardEvent } from 'react'
import PdfViewer from './PdfViewer'
import { preprocessForTts } from '../utils/tts'

interface SpeechRecognitionAlternative {
  transcript: string
}

interface SpeechRecognitionResult {
  0: SpeechRecognitionAlternative
}

interface SpeechRecognitionResultList {
  0: SpeechRecognitionResult
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string
}

interface SpeechRecognition extends EventTarget {
  lang: string
  interimResults: boolean
  maxAlternatives: number
  onresult: ((e: SpeechRecognitionEvent) => void) | null
  onerror: ((e: SpeechRecognitionErrorEvent) => void) | null
  onend: (() => void) | null
  start(): void
  abort(): void
}

type SpeechRecognitionConstructor = new () => SpeechRecognition

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor
    webkitSpeechRecognition?: SpeechRecognitionConstructor
  }
}

interface Source {
  text: string
  file: string
  page: number | null
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}

interface Props {
  sessionId: string
  onJumpToSlide?: (page: number) => void
}

/** Split answer text on (第N页) patterns and render inline citation links. */
function renderWithCitations(text: string, onPageClick: (page: number) => void): React.ReactNode {
  // First split on citation patterns, then handle newlines within plain segments
  const parts = text.split(/(\(第\d{1,3}页\)|（第\d{1,3}页）)/)
  const nodes: React.ReactNode[] = []
  parts.forEach((part, i) => {
    const m = part.match(/第(\d{1,3})页/)
    if (m) {
      const page = parseInt(m[1])
      nodes.push(
        <button
          key={i}
          onClick={() => onPageClick(page)}
          className="inline-flex items-center mx-0.5 px-1.5 py-0 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 hover:border-blue-400 transition-colors leading-5"
          title={`点击查看第 ${page} 页原文`}
        >
          第{page}页↗
        </button>
      )
    } else {
      // Render newlines as <br> so paragraph breaks are preserved
      part.split('\n').forEach((line, j, arr) => {
        nodes.push(<span key={`${i}-${j}`}>{line}</span>)
        if (j < arr.length - 1) nodes.push(<br key={`${i}-br-${j}`} />)
      })
    }
  })
  return nodes
}

function AssistantMessage({ msg, onViewPdf }: {
  msg: Message
  onViewPdf: (page: number) => void
}) {
  return (
    <div className="self-start bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-3 py-2 text-sm text-gray-800 max-w-[90%] leading-relaxed">
      {renderWithCitations(msg.content, onViewPdf)}
    </div>
  )
}

export default function ChatPanel({ sessionId }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [pdfPage, setPdfPage] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Fix 3: voice input — detect SR support
  const SR = typeof window !== 'undefined'
    ? (window.SpeechRecognition || window.webkitSpeechRecognition || null)
    : null
  const [listening, setListening] = useState(false)
  const [micError, setMicError] = useState<string | null>(null)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  // Fix 4: TTS with stop button
  const ttsSupported = typeof window !== 'undefined' && 'speechSynthesis' in window
  const [ttsEnabled, setTtsEnabled] = useState(false)
  const [ttsSpeaking, setTtsSpeaking] = useState(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Fix 4: stop TTS when toggle is turned off
  useEffect(() => {
    if (!ttsEnabled && ttsSpeaking) {
      window.speechSynthesis.cancel()
      setTtsSpeaking(false)
    }
  }, [ttsEnabled, ttsSpeaking])

  function stopTts() {
    window.speechSynthesis.cancel()
    setTtsSpeaking(false)
  }

  async function sendText(text: string) {
    const q = text.trim()
    if (!q || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setLoading(true)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, question: q }),
      })
      const data = await res.json()
      if (!res.ok) {
        setMessages(prev => [...prev, { role: 'assistant', content: `错误：${data.detail ?? '请求失败'}` }])
      } else {
        const answer: string = data.answer
        setMessages(prev => [...prev, { role: 'assistant', content: answer, sources: data.sources }])
        if (ttsEnabled && ttsSupported && answer) {
          window.speechSynthesis.cancel()
          const utterance = new SpeechSynthesisUtterance(preprocessForTts(answer))
          utterance.lang = 'zh-CN'
          utterance.onend = () => setTtsSpeaking(false)
          utterance.onerror = () => setTtsSpeaking(false)
          window.speechSynthesis.speak(utterance)
          setTtsSpeaking(true)
        }
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: '网络错误，请重试' }])
    } finally {
      setLoading(false)
    }
  }

  async function send() { await sendText(input) }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  // Fix 3: improved voice recognition with all error cases
  function startListening() {
    if (!SR) return
    setMicError(null)
    const recognition = new SR()
    recognition.lang = 'zh-CN'
    recognition.interimResults = false
    recognition.maxAlternatives = 1

    recognition.onresult = (e: SpeechRecognitionEvent) => {
      const transcript = e.results[0][0].transcript
      setListening(false)
      sendText(transcript)
    }

    recognition.onerror = (e: SpeechRecognitionErrorEvent) => {
      setListening(false)
      const msgs: Record<string, string> = {
        'not-allowed': '麦克风权限被拒绝，请在浏览器地址栏左侧点击锁图标开启权限',
        'no-speech': '未检测到语音，请重试',
        'network': '网络错误，语音识别需要联网',
        'service-not-allowed': '语音服务不可用（需要 Chrome/Edge）',
        'aborted': '',
      }
      const msg = msgs[e.error] ?? `识别失败：${e.error}`
      if (msg) setMicError(msg)
    }

    recognition.onend = () => setListening(false)

    recognitionRef.current = recognition
    try {
      recognition.start()
      setListening(true)
    } catch (e) {
      setMicError(`无法启动语音识别：${e}`)
    }
  }

  function stopListening() {
    recognitionRef.current?.abort()
    setListening(false)
  }

  return (
    <div className="flex flex-col min-h-0 h-full overflow-hidden border-l border-gray-200 bg-gray-50">
      {pdfPage !== null && (
        <PdfViewer sessionId={sessionId} page={pdfPage} onClose={() => setPdfPage(null)} />
      )}
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-white flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-700">论文问答</h3>
          <p className="text-xs text-gray-400">可以针对论文内容提问</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Fix 4: TTS stop button when speaking */}
          {ttsSupported && ttsSpeaking && (
            <button onClick={stopTts}
              className="text-xs px-2 py-1 border border-red-300 text-red-600 rounded hover:bg-red-50">
              ⏹ 停止朗读
            </button>
          )}
          {/* TTS toggle */}
          {ttsSupported && (
            <button
              onClick={() => setTtsEnabled(e => !e)}
              title={ttsEnabled ? '关闭自动朗读' : '开启自动朗读'}
              className={`text-lg px-2 py-1 rounded transition-colors ${ttsEnabled ? 'text-blue-600 bg-blue-50' : 'text-gray-400 hover:text-gray-600'}`}
            >
              {ttsEnabled ? '🔊' : '🔇'}
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        {messages.length === 0 && (
          <p className="text-xs text-gray-400 text-center mt-8">输入问题，向 AI 提问关于这篇论文的内容</p>
        )}
        {messages.map((msg, i) =>
          msg.role === 'user' ? (
            <div key={i} className="self-end bg-blue-600 text-white rounded-2xl rounded-tr-sm px-3 py-2 text-sm max-w-[90%] whitespace-pre-wrap">
              {msg.content}
            </div>
          ) : (
            <AssistantMessage key={i} msg={msg} onViewPdf={setPdfPage} />
          )
        )}
        {loading && (
          <div className="self-start bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-3 py-2 text-sm text-gray-400">思考中...</div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Mic error */}
      {micError && (
        <div className="px-4 py-2 bg-red-50 border-t border-red-100 text-xs text-red-600 flex justify-between">
          <span>{micError}</span>
          <button onClick={() => setMicError(null)} className="ml-2 text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {/* Input */}
      <div className="px-4 py-3 border-t border-gray-200 bg-white flex gap-2">
        <textarea
          rows={2}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={loading}
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
          className="flex-1 resize-none border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        {/* Fix 3: mic button */}
        {SR ? (
          <button
            onClick={listening ? stopListening : startListening}
            disabled={loading}
            title={listening ? '点击停止' : '点击后说话（需允许麦克风）'}
            className={`px-3 py-2 rounded-lg border text-sm self-end whitespace-nowrap ${
              listening ? 'border-red-300 bg-red-50 text-red-600 animate-pulse' : 'border-gray-300 text-gray-600 hover:bg-gray-100'
            } disabled:opacity-40`}
          >
            {listening ? '🎤 录音中' : '🎤'}
          </button>
        ) : (
          <span className="text-xs text-gray-300 self-end pb-2 cursor-not-allowed" title="语音输入需要 Chrome 或 Edge 浏览器">🎤</span>
        )}
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed self-end"
        >
          发送
        </button>
      </div>
    </div>
  )
}
