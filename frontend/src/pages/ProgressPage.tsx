import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'

interface Progress {
  ppt_step: string
  ppt_pct: number
  rag_step: string
  rag_pct: number
}

interface TaskStageState {
  task: string
  stage: string
  stage_label: string
  pct: number
  status: string
}

interface SessionStages {
  ppt: TaskStageState
  rag: TaskStageState
}

interface SessionPaths {
  project_dir?: string
  ppt_path?: string
  slides_dir?: string
  notes_dir?: string
}

interface LogItem {
  ts: string
  source: 'ppt' | 'rag' | 'system'
  level: 'INFO' | 'WARNING' | 'ERROR'
  stage: string
  message: string
  details?: Record<string, unknown> | null
}

interface SessionSnapshot {
  status?: string
  error?: string | null
  error_detail?: {
    message?: string
    source?: string
    stage?: string
    stdout_tail?: string | null
    stderr_tail?: string | null
  } | null
  progress?: Progress
  stages?: SessionStages
  recent_logs?: LogItem[]
  paths?: SessionPaths
}

function ProgressBar({ label, step, pct, status }: { label: string; step: string; pct: number; status?: string }) {
  return (
    <div className="w-full">
      <div className="flex justify-between text-sm text-gray-600 mb-1 gap-4">
        <span className="font-medium">{label}</span>
        <span className="text-right text-gray-400">
          {step || '等待中...'}
          {pct > 0 ? ` · ${pct}%` : ''}
          {status && status !== 'running' ? ` · ${status}` : ''}
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function formatTime(ts: string) {
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return ts
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

function levelClass(level: LogItem['level']) {
  if (level === 'ERROR') return 'text-red-600'
  if (level === 'WARNING') return 'text-amber-600'
  return 'text-gray-700'
}

function stageHint(task: 'ppt' | 'rag', stage?: string, step?: string) {
  if (task === 'ppt') {
    switch (stage) {
      case 'claude_started':
        return '已进入 Claude 执行阶段，正在解析论文与规划整套 PPT。'
      case 'claude_idle':
        return 'Claude 仍在持续生成；即使暂时没有新输出，也不代表任务卡死。'
      case 'skill_invocation':
        return '已触发 /ppt-master，正在进入批处理工作流。'
      case 'artifact_discovery':
        return 'Claude 已返回，后端正在定位项目目录与最终产物。'
      case 'notes_ready':
        return '已检测到讲稿文件，说明内容结构已经开始落盘。'
      case 'svg_output_ready':
        return '已检测到初版 SVG 页面，正在继续排版与补全。'
      case 'svg_final_ready':
        return '已检测到最终 SVG，正在准备导出 PPTX。'
      case 'pptx_ready':
        return '已检测到 PPTX 文件，正在收尾同步结果。'
      case 'complete':
        return 'PPT 产物已经全部完成，页面即将自动跳转。'
      default:
        return step ? `当前阶段：${step}` : '等待 PPT 任务启动...'
    }
  }

  switch (stage) {
    case 'cache_check':
      return '正在检查是否可复用已有索引。'
    case 'pdf_parse':
      return '正在解析 PDF 文本与结构。'
    case 'embedding':
      return '正在构建向量索引，这一步通常耗时较长。'
    case 'complete':
      return '知识库索引已构建完成。'
    default:
      return step ? `当前阶段：${step}` : '等待知识库任务启动...'
  }
}

function formatPathTail(path?: string) {
  if (!path) return ''
  const parts = path.split(/[/\\]/).filter(Boolean)
  return parts.slice(-3).join('/') || path
}

export default function ProgressPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { lastMessage, readyState } = useWebSocket(id!)
  const [progress, setProgress] = useState<Progress>({ ppt_step: '', ppt_pct: 0, rag_step: '', rag_pct: 0 })
  const [stages, setStages] = useState<SessionStages | null>(null)
  const [paths, setPaths] = useState<SessionPaths | null>(null)
  const [logs, setLogs] = useState<LogItem[]>([])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [errorDetail, setErrorDetail] = useState<SessionSnapshot['error_detail']>(null)
  const [done, setDone] = useState(false)
  const [connectionHint, setConnectionHint] = useState<string | null>(null)
  const [, setPollFailures] = useState(0)

  useEffect(() => {
    let cancelled = false
    const loadLogs = async () => {
      try {
        const res = await fetch(`/api/sessions/${id}/logs?limit=200`)
        if (!res.ok) {
          if (!cancelled) setConnectionHint('日志接口暂时不可用，稍后将继续重试。')
          return
        }
        const data = await res.json()
        if (Array.isArray(data.logs)) {
          setLogs(data.logs as LogItem[])
        }
      } catch {
        if (!cancelled) setConnectionHint('日志接口暂时不可用，稍后将继续重试。')
      }
    }
    loadLogs()
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    if (done || errorMsg) return

    let cancelled = false
    const syncSnapshot = async () => {
      try {
        const res = await fetch(`/api/sessions/${id}`)
        if (cancelled) return
        if (!res.ok) {
          setPollFailures(prev => {
            const next = prev + 1
            if (res.status === 404) {
              setErrorMsg('会话不存在或已失效，请重新上传文件。')
            } else if (next >= 2) {
              setConnectionHint('暂时无法获取最新进度，页面将继续重试。')
            }
            return next
          })
          return
        }
        setPollFailures(0)
        setConnectionHint(null)
        const data = await res.json() as SessionSnapshot
        if (data.progress) {
          const p = data.progress
          setProgress({
            ppt_step: p.ppt_step || '',
            ppt_pct: p.ppt_pct || 0,
            rag_step: p.rag_step || '',
            rag_pct: p.rag_pct || 0,
          })
        }
        if (data.stages) {
          setStages(data.stages)
        }
        if (data.paths) {
          setPaths(data.paths)
        }
        if (Array.isArray(data.recent_logs) && data.recent_logs.length > 0) {
          setLogs(data.recent_logs)
        }
        if (data.status === 'ready') {
          setProgress({ ppt_step: '完成', ppt_pct: 100, rag_step: '完成', rag_pct: 100 })
          setDone(true)
          setTimeout(() => navigate(`/session/${id}/ppt`), 800)
        } else if (data.status === 'error') {
          setErrorMsg(data.error || data.error_detail?.message || '处理失败')
          setErrorDetail(data.error_detail || null)
        }
      } catch {
        if (cancelled) return
        setPollFailures(prev => {
          const next = prev + 1
          if (next >= 2) {
            setConnectionHint('网络或后端暂不可用，正在继续重试。')
          }
          return next
        })
      }
    }

    syncSnapshot()
    const timer = setInterval(syncSnapshot, 8000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [id, done, errorMsg, navigate])

  useEffect(() => {
    if (!lastMessage) return

    if (lastMessage.terminal === true && typeof lastMessage.error === 'string') {
      setErrorMsg(lastMessage.error)
      return
    }

    if (lastMessage.event === 'progress') {
      const task = lastMessage.task as string
      const step = (lastMessage.stage_label as string) || (lastMessage.step as string)
      const pct = Number(lastMessage.progress_pct ?? lastMessage.pct ?? 0)
      const status = (lastMessage.status as string | undefined) ?? 'running'
      setProgress(prev => task === 'ppt'
        ? { ...prev, ppt_step: step, ppt_pct: pct }
        : { ...prev, rag_step: step, rag_pct: pct }
      )
      setStages(prev => {
        if (!prev) return prev
        return task === 'ppt'
          ? { ...prev, ppt: { ...prev.ppt, stage: String(lastMessage.stage ?? ''), stage_label: step, pct, status, task: 'ppt' } }
          : { ...prev, rag: { ...prev.rag, stage: String(lastMessage.stage ?? ''), stage_label: step, pct, status, task: 'rag' } }
      })
    } else if (lastMessage.event === 'log') {
      setLogs(prev => {
        const next = [...prev, lastMessage as unknown as LogItem]
        return next.slice(-200)
      })
    } else if (lastMessage.event === 'done') {
      setProgress(prev => ({ ...prev, ppt_pct: 100, rag_pct: 100 }))
      setDone(true)
      setTimeout(() => navigate(`/session/${id}/ppt`), 1200)
    } else if (lastMessage.event === 'error') {
      setErrorMsg((lastMessage.message as string) || '处理失败')
      setErrorDetail({
        message: lastMessage.message as string,
        source: lastMessage.source as string,
        stage: lastMessage.stage as string,
        stdout_tail: (lastMessage.stdout_tail as string | null | undefined) ?? null,
        stderr_tail: (lastMessage.stderr_tail as string | null | undefined) ?? null,
      })
    } else if ('status' in lastMessage) {
      const snap = lastMessage as SessionSnapshot
      const status = snap.status as string

      if (Array.isArray(snap.recent_logs) && snap.recent_logs.length > 0) {
        setLogs(snap.recent_logs)
      }

      if (snap.stages) {
        setStages(snap.stages)
      }

      if (snap.paths) {
        setPaths(snap.paths)
      }

      if (status === 'ready') {
        setProgress({ ppt_step: '完成', ppt_pct: 100, rag_step: '完成', rag_pct: 100 })
        setDone(true)
        setTimeout(() => navigate(`/session/${id}/ppt`), 1200)
        return
      }

      if (status === 'error') {
        setErrorMsg(snap.error || snap.error_detail?.message || '处理失败')
        setErrorDetail(snap.error_detail || null)
        return
      }

      if (snap.progress) {
        const p = snap.progress
        setProgress({
          ppt_step: p.ppt_step || '',
          ppt_pct: p.ppt_pct || 0,
          rag_step: p.rag_step || '',
          rag_pct: p.rag_pct || 0,
        })
      }
    }
  }, [lastMessage, id, navigate])

  const title = done ? '✓ 处理完成！' : '处理中...'

  const pptStage = stages?.ppt
  const ragStage = stages?.rag
  const latestPptLog = useMemo(() => [...logs].reverse().find(log => log.source === 'ppt'), [logs])
  const latestRagLog = useMemo(() => [...logs].reverse().find(log => log.source === 'rag'), [logs])
  const latestImportantLog = useMemo(
    () => [...logs].reverse().find(log => log.level !== 'INFO' || log.stage !== 'claude_output') ?? latestPptLog ?? latestRagLog ?? null,
    [logs, latestPptLog, latestRagLog],
  )

  const artifactState = useMemo(() => {
    const hasNotes = Boolean(paths?.notes_dir) || logs.some(log => log.stage === 'notes_ready')
    const hasSvgFinal = Boolean(paths?.slides_dir) || logs.some(log => log.stage === 'svg_final_ready')
    const hasPptx = Boolean(paths?.ppt_path) || logs.some(log => log.stage === 'pptx_ready')
    return { hasNotes, hasSvgFinal, hasPptx }
  }, [logs, paths])

  const pptHint = stageHint('ppt', pptStage?.stage, pptStage?.stage_label || progress.ppt_step)
  const ragHint = stageHint('rag', ragStage?.stage, ragStage?.stage_label || progress.rag_step)

  return (
    <div className="flex flex-col items-center justify-center flex-1 p-8">
      <div className="w-full max-w-3xl bg-white rounded-xl shadow-sm border border-gray-200 p-8 space-y-6">
        <h2 className="text-xl font-semibold text-gray-800">{title}</h2>

        {errorMsg ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700 text-sm font-medium">处理失败</p>
            <p className="text-red-600 text-sm mt-1">{errorMsg}</p>
            {errorDetail?.stage && (
              <p className="text-red-600 text-xs mt-2">阶段：{errorDetail.stage}</p>
            )}
            {errorDetail?.stderr_tail && (
              <pre className="mt-3 max-h-48 overflow-auto rounded bg-red-100 p-3 text-xs text-red-800 whitespace-pre-wrap">{errorDetail.stderr_tail}</pre>
            )}
            {errorDetail?.stdout_tail && (
              <pre className="mt-3 max-h-48 overflow-auto rounded bg-red-100 p-3 text-xs text-red-800 whitespace-pre-wrap">{errorDetail.stdout_tail}</pre>
            )}
            <Link to="/" className="mt-3 inline-block text-sm text-blue-600 hover:underline">
              ← 返回上传
            </Link>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-6">
              <div className="rounded-lg border border-blue-100 bg-blue-50/70 p-4 space-y-3">
                <ProgressBar
                  label="PPT 生成"
                  step={pptStage?.stage_label || progress.ppt_step}
                  pct={pptStage?.pct ?? progress.ppt_pct}
                  status={pptStage?.status}
                />
                <p className="text-sm text-blue-900">{pptHint}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-blue-950">
                  <div className="rounded bg-white/70 px-3 py-2 border border-blue-100">
                    <span className="font-medium">项目目录：</span>
                    {paths?.project_dir ? paths.project_dir : '尚未定位到最终项目目录'}
                  </div>
                  <div className="rounded bg-white/70 px-3 py-2 border border-blue-100">
                    <span className="font-medium">最近 PPT 日志：</span>
                    {latestPptLog ? `${formatTime(latestPptLog.ts)} ${latestPptLog.message}` : '等待第一条日志...'}
                  </div>
                  <div className="rounded bg-white/70 px-3 py-2 border border-blue-100 md:col-span-2">
                    <span className="font-medium">产物状态：</span>
                    <span className="ml-2">讲稿 {artifactState.hasNotes ? '✅' : '⏳'}</span>
                    <span className="ml-3">最终 SVG {artifactState.hasSvgFinal ? '✅' : '⏳'}</span>
                    <span className="ml-3">PPTX {artifactState.hasPptx ? '✅' : '⏳'}</span>
                    {(paths?.slides_dir || paths?.ppt_path) && (
                      <span className="ml-3 text-blue-800">
                        {formatPathTail(paths?.ppt_path || paths?.slides_dir)}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-emerald-100 bg-emerald-50/70 p-4 space-y-3">
                <ProgressBar
                  label="知识库构建"
                  step={ragStage?.stage_label || progress.rag_step}
                  pct={ragStage?.pct ?? progress.rag_pct}
                  status={ragStage?.status}
                />
                <p className="text-sm text-emerald-900">{ragHint}</p>
                <div className="rounded bg-white/70 px-3 py-2 border border-emerald-100 text-xs text-emerald-950">
                  <span className="font-medium">最近 RAG 日志：</span>
                  {latestRagLog ? `${formatTime(latestRagLog.ts)} ${latestRagLog.message}` : '等待第一条日志...'}
                </div>
              </div>

              {latestImportantLog && !errorMsg && (
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                  <span className="font-medium">当前提醒：</span>
                  <span className="ml-2">[{formatTime(latestImportantLog.ts)}] {latestImportantLog.message}</span>
                </div>
              )}

              {done && (
                <p className="text-green-600 text-sm text-center">正在跳转到 PPT 展示...</p>
              )}
              {readyState === 'connecting' && (
                <p className="text-gray-500 text-sm text-center">正在建立实时连接...</p>
              )}
              {readyState === 'reconnecting' && (
                <p className="text-amber-500 text-sm text-center">连接断开，正在重连...</p>
              )}
              {readyState === 'closed' && !done && !errorMsg && (
                <p className="text-amber-600 text-sm text-center">实时连接不可用，当前使用轮询获取进度。</p>
              )}
              {connectionHint && !errorMsg && (
                <p className="text-amber-600 text-sm text-center">{connectionHint}</p>
              )}
            </div>

            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-800">实时日志</h3>
                <span className="text-xs text-gray-400">最近 {logs.length} 条</span>
              </div>
              <div className="max-h-80 overflow-auto bg-gray-950 px-4 py-3 space-y-2">
                {logs.length === 0 ? (
                  <p className="text-sm text-gray-400">日志还没有产出，任务开始后会实时显示。</p>
                ) : logs.map((log, index) => (
                  <div key={`${log.ts}-${index}`} className="text-xs font-mono leading-5">
                    <span className="text-gray-500">[{formatTime(log.ts)}]</span>{' '}
                    <span className={levelClass(log.level)}>[{log.level}]</span>{' '}
                    <span className="text-cyan-400">[{log.source}]</span>{' '}
                    {log.stage ? <span className="text-violet-400">[{log.stage}]</span> : null}{' '}
                    <span className="text-gray-300">{log.message}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
