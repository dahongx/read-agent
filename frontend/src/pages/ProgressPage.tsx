import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'

interface Progress {
  ppt_step: string
  ppt_pct: number
  rag_step: string
  rag_pct: number
}

function ProgressBar({ label, step, pct }: { label: string; step: string; pct: number }) {
  return (
    <div className="w-full">
      <div className="flex justify-between text-sm text-gray-600 mb-1">
        <span className="font-medium">{label}</span>
        <span className="text-gray-400">{step || '等待中...'}{pct > 0 ? ` · ${pct}%` : ''}</span>
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

export default function ProgressPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { lastMessage, readyState } = useWebSocket(id!)
  const [progress, setProgress] = useState<Progress>({ ppt_step: '', ppt_pct: 0, rag_step: '', rag_pct: 0 })
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  // HTTP 轮询兜底：WebSocket done 事件万一丢失时，每 8 秒主动查一次
  useEffect(() => {
    if (done || errorMsg) return
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`/api/sessions/${id}`)
        if (!res.ok) return
        const data = await res.json()
        if (data.status === 'ready') {
          setProgress({ ppt_step: '完成', ppt_pct: 100, rag_step: '完成', rag_pct: 100 })
          setDone(true)
          setTimeout(() => navigate(`/session/${id}/ppt`), 800)
        } else if (data.status === 'error') {
          setErrorMsg(data.error || '处理失败')
        }
      } catch { /* ignore */ }
    }, 8000)
    return () => clearInterval(timer)
  }, [id, done, errorMsg, navigate])

  useEffect(() => {
    if (!lastMessage) return

    if (lastMessage.event === 'progress') {
      const task = lastMessage.task as string
      const step = lastMessage.step as string
      const pct = lastMessage.pct as number
      setProgress(prev => task === 'ppt'
        ? { ...prev, ppt_step: step, ppt_pct: pct }
        : { ...prev, rag_step: step, rag_pct: pct }
      )
    } else if (lastMessage.event === 'done') {
      setProgress(prev => ({ ...prev, ppt_pct: 100, rag_pct: 100 }))
      setDone(true)
      setTimeout(() => navigate(`/session/${id}/ppt`), 1200)
    } else if (lastMessage.event === 'error') {
      setErrorMsg(lastMessage.message as string)
    } else if ('status' in lastMessage) {
      // 初始快照（WebSocket 连上后立即收到完整 session 状态）
      const snap = lastMessage as Record<string, unknown>
      const status = snap.status as string

      // 如果连上时任务已经完成，直接跳转
      if (status === 'ready') {
        setProgress({ ppt_step: '完成', ppt_pct: 100, rag_step: '完成', rag_pct: 100 })
        setDone(true)
        setTimeout(() => navigate(`/session/${id}/ppt`), 1200)
        return
      }

      if (status === 'error') {
        setErrorMsg((snap.error as string) || '处理失败')
        return
      }

      // 恢复进度条（任务还在跑）
      if (snap.progress) {
        const p = snap.progress as Progress
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

  return (
    <div className="flex flex-col items-center justify-center flex-1 p-8">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-6">{title}</h2>

        {errorMsg ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700 text-sm font-medium">处理失败</p>
            <p className="text-red-600 text-sm mt-1">{errorMsg}</p>
            <Link to="/" className="mt-3 inline-block text-sm text-blue-600 hover:underline">
              ← 返回上传
            </Link>
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            <ProgressBar label="PPT 生成" step={progress.ppt_step} pct={progress.ppt_pct} />
            <ProgressBar label="知识库构建" step={progress.rag_step} pct={progress.rag_pct} />

            {done && (
              <p className="text-green-600 text-sm text-center">正在跳转到 PPT 展示...</p>
            )}
            {readyState === 'reconnecting' && (
              <p className="text-amber-500 text-sm text-center">连接断开，正在重连...</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
