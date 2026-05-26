import { getUserId } from './user'

export interface SpaceSummary {
  space_id: string
  paper_title: string
  pdf_filename: string
  session_type: 'single' | 'multi'
  config: Record<string, unknown> & {
    template?: string
    page_count?: number
    language?: string
    style?: string
    audience?: string
  }
  created_at?: number
  updated_at?: number
  state?: 'pending' | 'ready' | 'failed'
  error_message?: string | null
  ready: boolean
}

export interface SpaceDetail extends SpaceSummary {
  outputs?: {
    project_dir?: string
    ppt_path?: string
    slides_dir?: string
    notes_dir?: string
    merged_markdown_path?: string
  }
  source_documents?: Array<{
    doc_id: string
    order: number
    source_file_name: string
    pdf_path: string
  }>
}

export interface ConversationItem {
  id: string
  title: string
  msg_count: number
  created_at?: number
  updated_at?: number
}

export interface ConversationDetail extends ConversationItem {
  messages: Array<{
    role: 'user' | 'assistant'
    content: string
    sources?: unknown[]
    ts?: number
  }>
}

function userQuery(extra?: Record<string, string>): string {
  const params = new URLSearchParams()
  const uid = getUserId()
  if (uid) params.set('user_id', uid)
  if (extra) {
    for (const [k, v] of Object.entries(extra)) params.set(k, v)
  }
  return params.toString() ? `?${params.toString()}` : ''
}

async function jsonRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!res.ok) {
    let detail: unknown = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || data
    } catch {
      // ignore
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json() as Promise<T>
}

export async function listSpaces(): Promise<SpaceSummary[]> {
  const uid = getUserId() || 'anonymous'
  const data = await jsonRequest<{ spaces: SpaceSummary[] }>(
    `/api/users/${encodeURIComponent(uid)}/spaces`,
  )
  return data.spaces
}

export async function getSpace(spaceId: string): Promise<SpaceDetail> {
  return jsonRequest<SpaceDetail>(`/api/spaces/${spaceId}${userQuery()}`)
}

export async function listConversations(spaceId: string): Promise<ConversationItem[]> {
  const data = await jsonRequest<{ conversations: ConversationItem[] }>(
    `/api/spaces/${spaceId}/conversations${userQuery()}`,
  )
  return data.conversations
}

export async function getConversation(spaceId: string, convId: string): Promise<ConversationDetail> {
  return jsonRequest<ConversationDetail>(
    `/api/spaces/${spaceId}/conversations/${convId}${userQuery()}`,
  )
}

export async function createConversation(
  spaceId: string,
  title?: string,
): Promise<ConversationDetail> {
  return jsonRequest<ConversationDetail>(
    `/api/spaces/${spaceId}/conversations${userQuery(title ? { title } : undefined)}`,
    { method: 'POST' },
  )
}

export async function renameConversation(
  spaceId: string,
  convId: string,
  title: string,
): Promise<ConversationItem> {
  return jsonRequest<ConversationItem>(
    `/api/spaces/${spaceId}/conversations/${convId}${userQuery({ title })}`,
    { method: 'PATCH' },
  )
}

export async function deleteConversation(spaceId: string, convId: string): Promise<void> {
  await jsonRequest<{ deleted: boolean }>(
    `/api/spaces/${spaceId}/conversations/${convId}${userQuery()}`,
    { method: 'DELETE' },
  )
}

export async function deleteSpace(spaceId: string): Promise<void> {
  await jsonRequest<{ deleted: boolean }>(
    `/api/spaces/${spaceId}${userQuery()}`,
    { method: 'DELETE' },
  )
}
