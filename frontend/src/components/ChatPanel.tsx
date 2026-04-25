import React, { useEffect, useRef, useState, type KeyboardEvent } from 'react'
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
  doc_id?: string | null
  doc_order?: number | null
  source_file_name?: string | null
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

interface PdfTarget {
  page: number
  docId?: string | null
  fileLabel?: string | null
}

const INLINE_CITATION_SPLIT_REGEX = /(\(\s*第\s*\d{1,3}\s*页\s*\)|（\s*第\s*\d{1,3}\s*页\s*）)/u
const INLINE_CITATION_MATCH_REGEX = /第\s*(\d{1,3})\s*页/u

function sourceLabel(source: Source): string {
  return source.source_file_name || source.file
}

function renderPageLink(
  target: PdfTarget,
  key: React.Key,
  onPageClick: (target: PdfTarget) => void,
  label?: string,
) {
  return (
    <button
      key={key}
      onClick={() => onPageClick(target)}
      className="mx-0.5 inline-flex items-center rounded border border-blue-200 bg-blue-50 px-1.5 py-0 text-xs font-medium text-blue-600 transition-colors hover:border-blue-400 hover:bg-blue-100"
      title={`点击查看${target.fileLabel ? `${target.fileLabel} ` : ''}第 ${target.page} 页原文`}
    >
      {label ?? `第${target.page}页↗`}
    </button>
  )
}

function getFallbackSources(sources?: Source[]): Source[] {
  if (!sources?.length) return []

  const seen = new Set<string>()
  const items: Source[] = []

  for (const source of sources) {
    if (typeof source.page !== 'number') continue
    const key = `${source.doc_id ?? 'session'}:${source.page}`
    if (seen.has(key)) continue
    seen.add(key)
    items.push(source)
    if (items.length >= 4) break
  }

  return items
}


function findSourceForPage(sources: Source[] | undefined, page: number): Source | null {
  if (!sources?.length) return null

  const exactDocSource = sources.find(source => source.page === page && !!source.doc_id)
  if (exactDocSource) return exactDocSource

  return sources.find(source => source.page === page) ?? null
}

function renderWithCitations(
  text: string,
  sources: Source[] | undefined,
  onPageClick: (target: PdfTarget) => void,
): React.ReactNode {
  const parts = text.split(INLINE_CITATION_SPLIT_REGEX)
  const nodes: React.ReactNode[] = []

  parts.forEach((part, index) => {
    const match = part.match(INLINE_CITATION_MATCH_REGEX)
    if (match) {
      const page = Number.parseInt(match[1], 10)
      const source = findSourceForPage(sources, page)
      nodes.push(renderPageLink({
        page,
        docId: source?.doc_id,
        fileLabel: source ? sourceLabel(source) : null,
      }, index, onPageClick))
      return
    }

    part.split('\n').forEach((line, lineIndex, arr) => {
      nodes.push(<span key={`${index}-${lineIndex}`}>{line}</span>)
      if (lineIndex < arr.length - 1) {
        nodes.push(<br key={`${index}-br-${lineIndex}`} />)
      }
    })
  })

  return nodes
}

function AssistantMessage({
  msg,
  onViewPdf,
}: {
  msg: Message
  onViewPdf: (target: PdfTarget) => void
}) {
  const fallbackSources = getFallbackSources(msg.sources)

  return (
    <div className="max-w-[90%] self-start rounded-2xl rounded-tl-sm border border-gray-200 bg-white px-3 py-2 text-sm leading-relaxed text-gray-800">
      {renderWithCitations(msg.content, msg.sources, onViewPdf)}
      {fallbackSources.length > 0 && (
        <div className="mt-2 flex flex-col gap-1 text-xs text-gray-500">
          <span>参考出处：</span>
          <div className="flex flex-wrap gap-1">
            {fallbackSources.map((source, index) => renderPageLink(
              {
                page: source.page!,
                docId: source.doc_id,
                fileLabel: sourceLabel(source),
              },
              `fallback-${source.doc_id ?? 'session'}-${source.page}-${index}`,
              onViewPdf,
              `${sourceLabel(source)} 第${source.page}页↗`,
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function ChatPanel({ sessionId }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [pdfTarget, setPdfTarget] = useState<PdfTarget | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const SR = typeof window !== 'undefined'
    ? (window.SpeechRecognition || window.webkitSpeechRecognition || null)
    : null
  const [listening, setListening] = useState(false)
  const [micError, setMicError] = useState<string | null>(null)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  const ttsSupported = typeof window !== 'undefined' && 'speechSynthesis' in window
  const [ttsEnabled, setTtsEnabled] = useState(false)
  const [ttsSpeaking, setTtsSpeaking] = useState(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

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
    const question = text.trim()
    if (!question || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, question }),
      })

      const data = await res.json()
      if (!res.ok) {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: `错误：${data.detail ?? '请求失败'}` },
        ])
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

  async function send() {
    await sendText(input)
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send()
    }
  }

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
      void sendText(transcript)
    }

    recognition.onerror = (e: SpeechRecognitionErrorEvent) => {
      setListening(false)
      const messagesByCode: Record<string, string> = {
        'not-allowed': '麦克风权限被拒绝，请在浏览器地址栏左侧点击锁图标开启权限',
        'no-speech': '未检测到语音，请重试',
        network: '网络错误，语音识别需要联网',
        'service-not-allowed': '语音服务不可用（需要 Chrome/Edge）',
        aborted: '',
      }
      const message = messagesByCode[e.error] ?? `识别失败：${e.error}`
      if (message) setMicError(message)
    }

    recognition.onend = () => setListening(false)
    recognitionRef.current = recognition

    try {
      recognition.start()
      setListening(true)
    } catch (error) {
      setMicError(`无法启动语音识别：${String(error)}`)
    }
  }

  function stopListening() {
    recognitionRef.current?.abort()
    setListening(false)
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden border-l border-gray-200 bg-gray-50">
      {pdfTarget !== null && (
        <PdfViewer
          sessionId={sessionId}
          page={pdfTarget.page}
          docId={pdfTarget.docId}
          fileLabel={pdfTarget.fileLabel}
          onClose={() => setPdfTarget(null)}
        />
      )}

      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-700">论文问答</h3>
          <p className="text-xs text-gray-400">可以针对论文内容提问</p>
        </div>
        <div className="flex items-center gap-2">
          {ttsSupported && ttsSpeaking && (
            <button
              onClick={stopTts}
              className="rounded border border-red-300 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
            >
              ⏹ 停止朗读
            </button>
          )}
          {ttsSupported && (
            <button
              onClick={() => setTtsEnabled(enabled => !enabled)}
              title={ttsEnabled ? '关闭自动朗读' : '开启自动朗读'}
              className={`rounded px-2 py-1 text-lg transition-colors ${ttsEnabled ? 'bg-blue-50 text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
            >
              {ttsEnabled ? '🔊' : '🔈'}
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <p className="mt-8 text-center text-xs text-gray-400">
            输入问题，向 AI 提问关于这篇论文的内容
          </p>
        )}

        {messages.map((msg, index) => (
          msg.role === 'user' ? (
            <div
              key={index}
              className="max-w-[90%] self-end whitespace-pre-wrap rounded-2xl rounded-tr-sm bg-blue-600 px-3 py-2 text-sm text-white"
            >
              {msg.content}
            </div>
          ) : (
            <AssistantMessage key={index} msg={msg} onViewPdf={setPdfTarget} />
          )
        ))}

        {loading && (
          <div className="self-start rounded-2xl rounded-tl-sm border border-gray-200 bg-white px-3 py-2 text-sm text-gray-400">
            思考中...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {micError && (
        <div className="flex justify-between border-t border-red-100 bg-red-50 px-4 py-2 text-xs text-red-600">
          <span>{micError}</span>
          <button
            onClick={() => setMicError(null)}
            className="ml-2 text-red-400 hover:text-red-600"
          >
            ✕
          </button>
        </div>
      )}

      <div className="flex gap-2 border-t border-gray-200 bg-white px-4 py-3">
        <textarea
          rows={2}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={loading}
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
          className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        {SR ? (
          <button
            onClick={listening ? stopListening : startListening}
            disabled={loading}
            title={listening ? '点击停止' : '点击后说话（需允许麦克风）'}
            className={`self-end whitespace-nowrap rounded-lg border px-3 py-2 text-sm ${
              listening
                ? 'animate-pulse border-red-300 bg-red-50 text-red-600'
                : 'border-gray-300 text-gray-600 hover:bg-gray-100'
            } disabled:opacity-40`}
          >
            {listening ? '🎤 录音中' : '🎤'}
          </button>
        ) : (
          <span
            className="cursor-not-allowed self-end pb-2 text-xs text-gray-300"
            title="语音输入需要 Chrome 或 Edge 浏览器"
          >
            🎤
          </span>
        )}
        <button
          onClick={() => void send()}
          disabled={loading || !input.trim()}
          className="self-end rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          发送
        </button>
      </div>
    </div>
  )
}
