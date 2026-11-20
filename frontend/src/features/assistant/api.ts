import { useQuery } from '@tanstack/react-query'

import { useAuth } from '@/auth/useAuth'
import { api, ApiError } from '@/lib/api'

// Mirrors backend/app/features/assistant/schemas.py (ChatMessage, AssistantStatusOut).
export type ChatMessage = { role: 'user' | 'assistant'; content: string }

export type AssistantStatus = {
  /** False when the server has no OpenRouter key (or no docs): the page says so. */
  enabled: boolean
  model: string
  /** The docs the answers come from, e.g. "docs/features/F2-boundary.md". */
  documents: string[]
}

/** The server only reads the latest messages; sending more would only cost bandwidth. */
const CONTEXT_MESSAGES = 12

export function useAssistantStatus() {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['admin', 'assistant'],
    queryFn: () => api.get<AssistantStatus>('/admin/assistant'),
    enabled: user?.role === 'admin',
  })
}

/**
 * Ask the last question of `messages`. The answer streams back as plain text; `onText` gets each
 * piece as it arrives. Throws ApiError when the server refuses (not set up, rate limit, model
 * down) before answering.
 */
export async function askAssistant(
  messages: ChatMessage[],
  onText: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch('/api/admin/assistant/chat', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: messages.filter((m) => m.content.trim()).slice(-CONTEXT_MESSAGES),
    }),
    signal,
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    const detail = typeof data?.detail === 'string' ? data.detail : null
    throw new ApiError(res.status, detail ?? (res.statusText || 'The assistant could not answer'))
  }
  if (!res.body) {
    onText(await res.text())
    return
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    const text = decoder.decode(value, { stream: true })
    if (text) onText(text)
  }
  const rest = decoder.decode()
  if (rest) onText(rest)
}

// The conversation lives in this browser tab only (sessionStorage): nothing is kept on the
// server, a refresh keeps it, closing the tab or "Clear chat" ends it. Keyed by user, so a
// different account signing in on the same tab does not see it.
const storageKey = (userId: number) => `crvr.assistant.${userId}`

function isMessage(value: unknown): value is ChatMessage {
  const m = value as ChatMessage
  return (
    typeof m === 'object' &&
    m !== null &&
    (m.role === 'user' || m.role === 'assistant') &&
    typeof m.content === 'string'
  )
}

export function loadChat(userId: number): ChatMessage[] {
  try {
    const parsed: unknown = JSON.parse(sessionStorage.getItem(storageKey(userId)) ?? '[]')
    return Array.isArray(parsed) ? parsed.filter(isMessage) : []
  } catch {
    return []
  }
}

export function saveChat(userId: number, messages: ChatMessage[]) {
  try {
    if (messages.length) sessionStorage.setItem(storageKey(userId), JSON.stringify(messages))
    else sessionStorage.removeItem(storageKey(userId))
  } catch {
    // Storage blocked or full: the chat still works, it just won't survive a refresh.
  }
}
