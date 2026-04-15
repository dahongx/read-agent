import { useState, useRef } from 'react'
import type { DragEvent, ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'

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

export default function UploadPage() {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [config, setConfig] = useState<PptConfig>(DEFAULT_CONFIG)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  function setField<K extends keyof PptConfig>(key: K, value: PptConfig[K]) {
    setConfig(prev => ({ ...prev, [key]: value }))
  }

  function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('请选择 PDF 文件')
      return
    }
    setError(null)
    setSelectedFile(file)
  }

  async function upload() {
    if (!selectedFile) return
    setLoading(true)
    try {
      const form = new FormData()
      form.append('file', selectedFile)
      form.append('ppt_config', JSON.stringify(config))
      const res = await fetch('/api/upload', { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) {
        setError(formatUploadError(data.detail))
        return
      }
      navigate(`/session/${data.session_id}`)
    } catch {
      setError('网络错误，请重试')
    } finally {
      setLoading(false)
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div className="flex flex-col items-center justify-center flex-1 p-8 gap-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-gray-800 mb-1">上传论文</h1>
        <p className="text-gray-500 text-sm">上传 PDF，配置 PPT 参数，自动生成演示文稿并建立问答知识库</p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !loading && inputRef.current?.click()}
        className={`
          w-full max-w-xl border-2 border-dashed rounded-xl p-8
          flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors
          ${dragging ? 'border-blue-500 bg-blue-50' : selectedFile ? 'border-green-400 bg-green-50' : 'border-gray-300 bg-white hover:border-blue-400 hover:bg-gray-50'}
          ${loading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        {selectedFile ? (
          <>
            <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-green-700 font-medium text-sm">{selectedFile.name}</p>
            <p className="text-gray-400 text-xs">点击重新选择</p>
          </>
        ) : (
          <>
            <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-gray-600 font-medium text-sm">拖拽 PDF 到此处，或点击选择文件</p>
            <p className="text-gray-400 text-xs">仅支持 .pdf 格式</p>
          </>
        )}
      </div>
      <input ref={inputRef} type="file" accept=".pdf" className="hidden" onChange={onFileChange} disabled={loading} />

      {/* Config form */}
      <div className="w-full max-w-xl bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-gray-700">PPT 最终确认配置</h2>
        <p className="text-xs text-gray-500">
          所选配置将作为最终确认直接进入自动生成，不再二次询问。
        </p>

        {/* Template */}
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

        {/* Other fields */}
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
        disabled={!selectedFile || loading}
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
        ) : '上传并生成 PPT'}
      </button>
    </div>
  )
}
