import { useEffect, useRef, useState } from 'react'
import type { DragEvent, ChangeEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useUserId } from '../utils/user'
import { deleteSpace, listSpaces, type SpaceSummary } from '../utils/api'

type UploadMode = 'single' | 'multi'

interface PptConfig {
  template: string
  page_count: number
  language: string
  style: string
  audience: string
}

const TEMPLATES = [
  { value: 'academic_defense', label: '学术答辩', desc: '适合论文汇报、研究展示' },
  { value: 'anthropic', label: 'Anthropic 风格', desc: '科技感，适合AI/LLM内容' },
  { value: 'google_style', label: 'Google 风格', desc: '简洁现代，适合技术分享' },
  { value: 'mckinsey', label: '麦肯锡风格', desc: '咨询风，数据驱动' },
  { value: 'exhibit', label: 'Exhibit 风格', desc: '结论优先，适合战略汇报' },
  { value: '重庆大学', label: '重庆大学', desc: '高校专属，学术答辩场景' },
  { value: 'no_template', label: '自由设计', desc: '不使用模板，AI自由发挥' },
]

const DEFAULT_CONFIG: PptConfig = {
  template: 'academic_defense',
  page_count: 12,
  language: '中文',
  style: '学术汇报',
  audience: '高校师生',
}

function formatUploadError(detail: unknown): string {
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map(item => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') {
          const record = item as { loc?: unknown; msg?: unknown }
          const loc = Array.isArray(record.loc)
            ? record.loc.filter(part => typeof part === 'string' || typeof part === 'number').join('.')
            : ''
          const msg = typeof record.msg === 'string' ? record.msg : ''
          if (loc && msg) return `${loc}: ${msg}`
          if (msg) return msg
          return JSON.stringify(item)
        }
        return String(item)
      })
      .filter(Boolean)

    if (messages.length > 0) {
      return messages.join('；')
    }
  }

  if (detail && typeof detail === 'object') {
    return JSON.stringify(detail)
  }

  return '上传失败'
}

function isPdfFile(file: File): boolean {
  return file.name.toLowerCase().endsWith('.pdf')
}

function formatFileSummary(files: File[]): string {
  if (files.length === 0) return ''
  if (files.length === 1) return files[0].name
  return `${files.length} 个文件：${files.slice(0, 3).map(file => file.name).join('、')}${files.length > 3 ? ' ...' : ''}`
}

export default function UploadPage() {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [config, setConfig] = useState<PptConfig>(DEFAULT_CONFIG)
  const [uploadMode, setUploadMode] = useState<UploadMode>('single')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [userId, setUserId] = useUserId()
  const [userInput, setUserInput] = useState(userId)
  const [history, setHistory] = useState<SpaceSummary[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    setUserInput(userId)
  }, [userId])

  useEffect(() => {
    if (!userId) {
      setHistory([])
      return
    }
    let cancelled = false
    setHistoryLoading(true)
    listSpaces()
      .then(spaces => { if (!cancelled) setHistory(spaces) })
      .catch(() => { if (!cancelled) setHistory([]) })
      .finally(() => { if (!cancelled) setHistoryLoading(false) })
    return () => { cancelled = true }
  }, [userId])

  function commitUserId() {
    const trimmed = userInput.trim()
    if (trimmed && trimmed !== userId) {
      setUserId(trimmed)
    }
  }

  async function refreshHistory() {
    if (!userId) return
    try {
      const spaces = await listSpaces()
      setHistory(spaces)
    } catch {
      // ignore
    }
  }

  async function handleDeleteSpace(spaceId: string, label: string) {
    if (!confirm(`确认删除空间「${label}」？该用户在此空间下的所有会话也会一起删除（PPT/RAG 缓存保留）。`)) return
    try {
      await deleteSpace(spaceId)
      await refreshHistory()
    } catch (err) {
      alert(`删除失败：${(err as Error).message}`)
    }
  }

  function setField<K extends keyof PptConfig>(key: K, value: PptConfig[K]) {
    setConfig(prev => ({ ...prev, [key]: value }))
  }

  function switchMode(mode: UploadMode) {
    setUploadMode(mode)
    setError(null)
    setSelectedFile(null)
    setSelectedFiles([])
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  function handleSingleFile(file: File) {
    if (!isPdfFile(file)) {
      setError('请选择 PDF 文件')
      return
    }
    setError(null)
    setSelectedFile(file)
  }

  function handleMultiFiles(files: File[]) {
    const invalidFiles = files.filter(file => !isPdfFile(file))
    if (invalidFiles.length > 0) {
      setError(`仅支持 PDF 文件：${invalidFiles.map(file => file.name).join('、')}`)
      return
    }
    if (files.length < 2) {
      setError('多篇综述模式至少需要选择 2 个 PDF 文件')
      return
    }
    setError(null)
    setSelectedFiles(files)
  }

  function handleInputFiles(files: FileList | File[]) {
    const normalized = Array.from(files)
    if (uploadMode === 'single') {
      const file = normalized[0]
      if (file) handleSingleFile(file)
      return
    }
    handleMultiFiles(normalized)
  }

  async function upload() {
    const hasValidSelection = uploadMode === 'single' ? !!selectedFile : selectedFiles.length >= 2
    if (!hasValidSelection) return

    if (!userId.trim()) {
      setError('请先在右上角输入用户名')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('ppt_config', JSON.stringify(config))
      form.append('user_id', userId.trim())

      let endpoint = '/api/upload'
      if (uploadMode === 'single' && selectedFile) {
        form.append('file', selectedFile)
      } else {
        endpoint = '/api/upload-multi'
        selectedFiles.forEach(file => form.append('files', file))
      }

      const res = await fetch(endpoint, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) {
        setError(formatUploadError(data.detail))
        return
      }
      navigate(`/tasks/${data.session_id}?space=${encodeURIComponent(data.space_id || '')}`)
    } catch {
      setError('网络错误，请重试')
    } finally {
      setLoading(false)
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
    handleInputFiles(e.dataTransfer.files)
  }

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      handleInputFiles(e.target.files)
    }
  }

  const selectedSummary = uploadMode === 'single'
    ? selectedFile?.name ?? ''
    : formatFileSummary(selectedFiles)
  const hasSelection = uploadMode === 'single' ? !!selectedFile : selectedFiles.length >= 2
  const title = uploadMode === 'single' ? '上传单篇论文' : '上传多篇论文综述'
  const subtitle = uploadMode === 'single'
    ? '上传单篇 PDF，配置 PPT 参数，自动生成演示文稿并建立问答知识库'
    : '上传多篇 PDF，自动生成综述 PPT，并建立联合问答知识库'

  return (
    <div className="flex flex-col items-center justify-center flex-1 p-8 gap-6">
      <div className="w-full max-w-xl flex items-center gap-2 bg-white border border-gray-200 rounded-xl px-4 py-2 text-sm">
        <span className="text-gray-500 shrink-0">用户名</span>
        <input
          value={userInput}
          onChange={e => setUserInput(e.target.value)}
          onBlur={commitUserId}
          onKeyDown={e => { if (e.key === 'Enter') commitUserId() }}
          placeholder="输入一个名字以保存历史与会话"
          className="flex-1 px-2 py-1 outline-none focus:ring-2 focus:ring-blue-500 rounded"
        />
        {userId && (
          <span className="text-xs text-gray-400 shrink-0">当前：{userId}</span>
        )}
      </div>

      <div className="text-center">
        <h1 className="text-2xl font-semibold text-gray-800 mb-1">{title}</h1>
        <p className="text-gray-500 text-sm">{subtitle}</p>
      </div>

      <div className="w-full max-w-xl bg-white border border-gray-200 rounded-xl p-3 grid grid-cols-2 gap-2">
        <button
          onClick={() => switchMode('single')}
          disabled={loading}
          className={`px-4 py-3 rounded-lg text-sm text-left transition-colors ${
            uploadMode === 'single'
              ? 'bg-blue-50 border border-blue-500 text-blue-700'
              : 'border border-transparent text-gray-700 hover:bg-gray-50'
          }`}
        >
          <div className="font-medium">单篇</div>
          <div className="text-xs text-gray-400 mt-1">生成单篇 PPT + RAG</div>
        </button>
        <button
          onClick={() => switchMode('multi')}
          disabled={loading}
          className={`px-4 py-3 rounded-lg text-sm text-left transition-colors ${
            uploadMode === 'multi'
              ? 'bg-blue-50 border border-blue-500 text-blue-700'
              : 'border border-transparent text-gray-700 hover:bg-gray-50'
          }`}
        >
          <div className="font-medium">多篇综述</div>
          <div className="text-xs text-gray-400 mt-1">生成综述 PPT + 联合 RAG</div>
        </button>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !loading && inputRef.current?.click()}
        className={`
          w-full max-w-xl border-2 border-dashed rounded-xl p-8
          flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors
          ${dragging ? 'border-blue-500 bg-blue-50' : hasSelection ? 'border-green-400 bg-green-50' : 'border-gray-300 bg-white hover:border-blue-400 hover:bg-gray-50'}
          ${loading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        {hasSelection ? (
          <>
            <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-green-700 font-medium text-sm text-center break-all">{selectedSummary}</p>
            <p className="text-gray-400 text-xs">点击重新选择</p>
          </>
        ) : (
          <>
            <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-gray-600 font-medium text-sm">
              {uploadMode === 'single' ? '拖拽 PDF 到此处，或点击选择文件' : '拖拽多个 PDF 到此处，或点击选择文件'}
            </p>
            <p className="text-gray-400 text-xs">
              {uploadMode === 'single' ? '仅支持单个 .pdf 文件' : '仅支持 .pdf 格式，至少 2 个文件'}
            </p>
          </>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        multiple={uploadMode === 'multi'}
        className="hidden"
        onChange={onFileChange}
        disabled={loading}
      />

      <div className="w-full max-w-xl bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-gray-700">PPT 最终确认配置</h2>
        <p className="text-xs text-gray-500">
          所选配置将作为最终确认直接进入自动生成，不再二次询问。
        </p>

        <div>
          <label className="block text-xs text-gray-500 mb-1.5">模板风格</label>
          <div className="grid grid-cols-2 gap-2">
            {TEMPLATES.map(t => (
              <button
                key={t.value}
                onClick={() => setField('template', t.value)}
                className={`text-left px-3 py-2 rounded-lg border text-xs transition-colors ${
                  config.template === t.value
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-700'
                }`}
              >
                <div className="font-medium">{t.label}</div>
                <div className="text-gray-400 mt-0.5">{t.desc}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">页数</label>
            <select
              value={config.page_count}
              onChange={e => setField('page_count', parseInt(e.target.value))}
              className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {[8, 10, 12, 15, 20].map(n => <option key={n} value={n}>{n} 页</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">语言</label>
            <select
              value={config.language}
              onChange={e => setField('language', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option>中文</option>
              <option>英文</option>
              <option>中英双语</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">风格</label>
            <select
              value={config.style}
              onChange={e => setField('style', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option>学术汇报</option>
              <option>商务简报</option>
              <option>技术分享</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">受众</label>
            <select
              value={config.audience}
              onChange={e => setField('audience', e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option>高校师生</option>
              <option>企业团队</option>
              <option>通用</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-2">
          {error}
        </p>
      )}

      <button
        onClick={upload}
        disabled={!hasSelection || loading}
        className="w-full max-w-xl py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            上传中...
          </>
        ) : uploadMode === 'single' ? '上传并生成 PPT' : '上传并生成综述 PPT'}
      </button>

      {userId && (
        <div className="w-full max-w-xl mt-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-700">我的历史空间</h3>
            <span className="text-xs text-gray-400">
              {historyLoading ? '加载中...' : `${history.length} 条`}
            </span>
          </div>
          {history.length === 0 && !historyLoading && (
            <p className="text-xs text-gray-400 bg-gray-50 border border-dashed border-gray-200 rounded-lg px-4 py-6 text-center">
              暂无生成历史。上传一篇论文后会出现在这里。
            </p>
          )}
          <div className="flex flex-col gap-2">
            {history.map(space => {
              const state = space.state || (space.ready ? 'ready' : 'pending')
              const stateClass =
                state === 'ready'
                  ? 'bg-green-50 text-green-700 border-green-200'
                  : state === 'failed'
                  ? 'bg-red-50 text-red-700 border-red-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              const stateLabel = state === 'ready' ? '可阅读' : state === 'failed' ? '已失败' : '处理中'
              const label = space.paper_title || space.pdf_filename
              const inner = (
                <div className="flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{label}</p>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">
                      {space.session_type === 'multi' ? '多篇综述' : '单篇'}
                      {' · '}
                      {space.config?.template || ''}
                      {' · '}
                      {space.config?.page_count || ''} 页
                      {' · '}
                      {space.config?.style || ''}
                    </p>
                    {state === 'failed' && space.error_message && (
                      <p className="text-xs text-red-500 mt-0.5 truncate" title={space.error_message}>
                        {space.error_message}
                      </p>
                    )}
                  </div>
                  <span className={`text-xs shrink-0 px-2 py-0.5 rounded-full border ${stateClass}`}>
                    {stateLabel}
                  </span>
                  <button
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleDeleteSpace(space.space_id, label) }}
                    className="text-xs text-gray-300 hover:text-red-500 px-1"
                    title="删除空间"
                  >
                    ✕
                  </button>
                </div>
              )
              return state === 'ready' ? (
                <Link
                  key={space.space_id}
                  to={`/space/${space.space_id}`}
                  className="block bg-white border border-gray-200 rounded-lg px-4 py-3 hover:border-blue-300 hover:bg-blue-50/40 transition-colors"
                >
                  {inner}
                </Link>
              ) : (
                <div
                  key={space.space_id}
                  className="block bg-white border border-gray-200 rounded-lg px-4 py-3 cursor-not-allowed opacity-80"
                >
                  {inner}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
