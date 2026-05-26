import React, { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import PdfViewer from './PdfViewer'
import { preprocessForTts } from '../utils/tts'
import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  type ConversationItem,
} from '../utils/api'
import { getUserId } from '../utils/user'

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
  quote?: string | null
  chunk_id?: number | null
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}

interface Props {
  spaceId: string
  onJumpToSlide?: (page: number) => void
}

interface PdfTarget {
  page: number
  docId?: string | null
  fileLabel?: string | null
  quote?: string | null
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

function findSourceForPage(sources: Source[] | undefined, page: number): Source | null {
  if (!sources?.length) return null
  const withQuote = sources.find(source => source.page === page && !!source.quote)
  if (withQuote) return withQuote
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
        quote: source?.quote ?? null,
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
  return (
    <div className="max-w-[90%] self-start rounded-2xl rounded-tl-sm border border-gray-200 bg-white px-3 py-2 text-sm leading-relaxed text-gray-800">
      {renderWithCitations(msg.content, msg.sources, onViewPdf)}
    </div>
  )
}

export default function ChatPanel({ spaceId }: Props) {
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [activeConvId, setActiveConvId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [pdfTarget, setPdfTarget] = useState<PdfTarget | null>(null)
  const [convMenuOpen, setConvMenuOpen] = useState(false)
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

  // 进入空间时加载会话列表 + 自动选最近一个 / 新建一个
  useEffect(() => {
    if (!spaceId) return
    let cancelled = false
    async function init() {
      try {
        const items = await listConversations(spaceId)
        if (cancelled) return
        if (items.length > 0) {
          setConversations(items)
          setActiveConvId(items[0].id)
        } else {
          const conv = await createConversation(spaceId)
          if (cancelled) return
          setConversations([{
            id: conv.id, title: conv.title, msg_count: 0,
            created_at: conv.created_at, updated_at: conv.updated_at,
          }])
          setActiveConvId(conv.id)
        }
      } catch (err) {
        console.error('init conversations failed', err)
      }
    }
    init()
    return () => { cancelled = true }
  }, [spaceId])

  // 切换会话时拉取消息
  useEffect(() => {
    if (!spaceId || !activeConvId) return
    let cancelled = false
    async function loadMessages() {
      try {
        const conv = await getConversation(spaceId, activeConvId!)
        if (cancelled) return
        setMessages((conv.messages || []).map(m => ({
          role: m.role,
          content: m.content,
          sources: (m.sources as Source[] | undefined) || undefined,
        })))
      } catch (err) {
        console.error('load conversation failed', err)
        setMessages([])
      }
    }
    loadMessages()
    return () => { cancelled = true }
  }, [spaceId, activeConvId])

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

  async function refreshConversations(preferConvId?: string) {
    try {
      const items = await listConversations(spaceId)
      setConversations(items)
      if (preferConvId && items.some(i => i.id === preferConvId)) {
        setActiveConvId(preferConvId)
      } else if (items.length > 0 && !items.some(i => i.id === activeConvId)) {
        setActiveConvId(items[0].id)
      } else if (items.length === 0) {
        setActiveConvId(null)
      }
    } catch (err) {
      console.error('refresh conversations failed', err)
    }
  }

  async function handleNewConversation() {
    try {
      const conv = await createConversation(spaceId)
      await refreshConversations(conv.id)
      setMessages([])
      setConvMenuOpen(false)
    } catch (err) {
      alert(`新建会话失败：${(err as Error).message}`)
    }
  }

  async function handleDeleteConversation(convId: string) {
    if (!confirm('确认删除这个会话吗？')) return
    try {
      await deleteConversation(spaceId, convId)
      // 若删的是当前会话，列表里没了就自动切换或新建
      const remaining = conversations.filter(c => c.id !== convId)
      if (remaining.length > 0) {
        await refreshConversations(remaining[0].id)
      } else {
        const conv = await createConversation(spaceId)
        await refreshConversations(conv.id)
        setMessages([])
      }
    } catch (err) {
      alert(`删除失败：${(err as Error).message}`)
    }
  }

  async function sendText(text: string) {
    const question = text.trim()
    if (!question || loading || !activeConvId) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          space_id: spaceId,
          conversation_id: activeConvId,
          user_id: getUserId() || 'anonymous',
          question,
        }),
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

        if (data.conversation_title) {
          // 后端首条问答自动起标题，刷新列表显示
          refreshConversations(activeConvId)
        }

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

  // PdfViewer：把目标的 pdfPath 改成 spaces API
  const pdfBaseUrl = pdfTarget
    ? (pdfTarget.docId
        ? `/api/spaces/${spaceId}/pdf/${encodeURIComponent(pdfTarget.docId)}`
        : `/api/spaces/${spaceId}/pdf`)
    : ''

  const activeConv = conversations.find(c => c.id === activeConvId)

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden border-l border-gray-200 bg-gray-50">
      {pdfTarget !== null && (
        <PdfViewer
          pdfUrl={pdfBaseUrl}
          page={pdfTarget.page}
          fileLabel={pdfTarget.fileLabel}
          quote={pdfTarget.quote ?? null}
          onClose={() => setPdfTarget(null)}
        />
      )}

      {/* 顶部：标题 + 会话切换条 */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-gray-700 shrink-0">论文问答</h3>
          <div className="relative min-w-0">
            <button
              onClick={() => setConvMenuOpen(o => !o)}
              className="flex items-center gap-1 max-w-[200px] truncate rounded border border-gray-200 bg-gray-50 px-2 py-1 text-xs text-gray-700 hover:border-blue-300"
              title={activeConv?.title}
            >
              <span className="truncate">{activeConv?.title || '加载中...'}</span>
              <span className="text-gray-400">▾</span>
            </button>
            {convMenuOpen && (
              <div className="absolute left-0 top-full mt-1 w-72 max-h-80 overflow-auto rounded-lg border border-gray-200 bg-white shadow-lg z-30">
                <div className="sticky top-0 flex items-center justify-between border-b border-gray-200 bg-white px-3 py-2">
                  <span className="text-xs text-gray-500">会话列表（{conversations.length}/50）</span>
                  <button
                    onClick={handleNewConversation}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    + 新建
                  </button>
                </div>
                {conversations.length === 0 ? (
                  <p className="px-3 py-4 text-xs text-gray-400">暂无会话</p>
                ) : (
                  <ul className="py-1">
                    {conversations.map(conv => (
                      <li key={conv.id} className="group flex items-center justify-between px-3 py-1.5 text-xs hover:bg-blue-50">
                        <button
                          onClick={() => {
                            setActiveConvId(conv.id)
                            setConvMenuOpen(false)
                          }}
                          className={`flex-1 truncate text-left ${conv.id === activeConvId ? 'text-blue-700 font-medium' : 'text-gray-700'}`}
                          title={conv.title}
                        >
                          {conv.title}
                          <span className="ml-1 text-gray-400">·{conv.msg_count}</span>
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDeleteConversation(conv.id) }}
                          className="ml-2 text-gray-300 opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-500"
                          title="删除"
                        >
                          ✕
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {ttsSupported && ttsSpeaking && (
            <button
              onClick={stopTts}
              className="rounded border border-red-300 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
            >
              ⏹
            </button>
          )}
          {ttsSupported && (
            <button
              onClick={() => setTtsEnabled(enabled => !enabled)}
              title={ttsEnabled ? '关闭自动朗读' : '开启自动朗读'}
              className={`rounded px-2 py-1 text-base transition-colors ${ttsEnabled ? 'bg-blue-50 text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
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
          disabled={loading || !activeConvId}
          placeholder={activeConvId ? '输入问题，Enter 发送，Shift+Enter 换行' : '正在加载会话...'}
          className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        {SR ? (
          <button
            onClick={listening ? stopListening : startListening}
            disabled={loading || !activeConvId}
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
          disabled={loading || !input.trim() || !activeConvId}
          className="self-end rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          发送
        </button>
      </div>
    </div>
  )
}
