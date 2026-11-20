import { type FormEvent, useEffect, useRef, useState } from 'react'

import { useAuth } from '@/auth/useAuth'
import { Alert, Button, Card, Icon, PageHeader, Textarea } from '@/components/ui'

import { askAssistant, type ChatMessage, loadChat, saveChat, useAssistantStatus } from './api'
import { Markdown } from './Markdown'

const EXAMPLES = [
  'What does each feature F1–F5 do, and who owns it?',
  'How does overlap detection decide when a boundary blocks submission?',
  'How is the audit ledger made tamper-evident?',
  'How is the demo deployed on Google Cloud, and what does it cost?',
]

/**
 * F5 — System › Assistant. Admins ask about CRVR (features, design, how it was built); answers
 * come from the project docs through an AI model. The chat stays in this browser tab only.
 */
export function AssistantPage() {
  const { user } = useAuth()
  const userId = user?.id ?? 0
  const status = useAssistantStatus()
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadChat(userId))
  const [question, setQuestion] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const abort = useRef<AbortController | null>(null)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => saveChat(userId, messages), [userId, messages])
  useEffect(() => bottom.current?.scrollIntoView?.({ block: 'end' }), [messages])
  useEffect(() => () => abort.current?.abort(), [])

  const enabled = status.data?.enabled ?? false

  async function ask(text: string) {
    const asked = text.trim()
    if (!asked || busy) return
    const conversation: ChatMessage[] = [...messages, { role: 'user', content: asked }]
    setMessages([...conversation, { role: 'assistant', content: '' }])
    setQuestion('')
    setError(null)
    setBusy(true)
    const controller = new AbortController()
    abort.current = controller
    let answered = false
    const append = (piece: string) => {
      answered = true
      setMessages((all) => {
        const last = all.at(-1)
        if (last?.role !== 'assistant') return all
        return [...all.slice(0, -1), { ...last, content: last.content + piece }]
      })
    }
    try {
      await askAssistant(conversation, append, controller.signal)
    } catch (e) {
      const message = e instanceof Error ? e.message : 'The assistant could not answer.'
      if (answered) {
        // Part of an answer arrived: keep it and say where it ended.
        append(controller.signal.aborted ? '\n\n_(Stopped.)_' : '\n\n_(The answer was cut off.)_')
      } else {
        // No answer: take the question back out of the chat and into the box to try again.
        setMessages((all) => all.slice(0, -2))
        setQuestion(asked)
        if (!controller.signal.aborted) setError(message)
      }
    } finally {
      abort.current = null
      setBusy(false)
    }
  }

  function clear() {
    abort.current?.abort()
    setMessages([])
    setError(null)
  }

  function submit(e: FormEvent) {
    e.preventDefault()
    void ask(question)
  }

  return (
    <>
      <PageHeader
        title="Assistant"
        subtitle="Ask about CRVR: what each feature does, how it works and how we built it"
        actions={
          <Button
            variant="ghost"
            className="w-auto px-3 py-2"
            onClick={clear}
            disabled={messages.length === 0}
          >
            Clear chat
          </Button>
        }
      />

      {status.isError && (
        <Alert className="mb-3" title="The assistant could not be loaded">
          {status.error.message}
        </Alert>
      )}
      {status.data && !enabled && (
        <Alert className="mb-3" title="The assistant is not set up on this server" icon="lock">
          It needs an OpenRouter API key (<code className="font-mono">OPENROUTER_API_KEY</code>
          ). See <code className="font-mono">docs/features/F5-security-audit.md</code>.
        </Alert>
      )}

      <Card className="flex flex-col">
        <div
          className="max-h-[calc(100dvh-22rem)] min-h-64 overflow-y-auto p-4"
          aria-live="polite"
          aria-busy={busy}
        >
          {messages.length === 0 ? (
            <div className="grid justify-items-center gap-2 py-6 text-center">
              <span className="mb-1 grid size-11 place-items-center rounded-full bg-accent-soft text-accent">
                <Icon name="chat" className="size-[22px]" />
              </span>
              <b className="text-[15px] font-semibold text-ink">Ask anything about CRVR</b>
              <p className="max-w-md text-[13px] text-faint">
                Answers come from the project docs: the five feature docs, architecture, decisions
                and deployment. For example:
              </p>
              <div className="mt-2 grid w-full max-w-xl gap-2">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    disabled={!enabled || busy}
                    onClick={() => void ask(example)}
                    className="rounded-lg border border-line bg-surface px-3 py-2 text-left text-sm text-muted transition-colors hover:border-accent hover:text-ink disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <ol className="grid gap-4" aria-label="Conversation">
              {messages.map((m, i) =>
                m.role === 'user' ? (
                  <li
                    key={i}
                    className="ml-auto max-w-[85%] rounded-xl bg-accent-soft px-3.5 py-2.5 text-sm whitespace-pre-wrap text-ink"
                  >
                    <span className="sr-only">You: </span>
                    {m.content}
                  </li>
                ) : (
                  <li key={i} className="flex max-w-full gap-2.5">
                    <span className="mt-0.5 grid size-7 flex-none place-items-center rounded-full bg-surface-2 text-accent">
                      <Icon name="chat" className="size-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <span className="sr-only">Assistant: </span>
                      {m.content ? (
                        <Markdown>{m.content}</Markdown>
                      ) : (
                        <p className="text-sm text-faint">Reading the docs…</p>
                      )}
                    </div>
                  </li>
                ),
              )}
            </ol>
          )}
          <div ref={bottom} />
        </div>

        <form onSubmit={submit} className="border-t border-line p-3">
          {error && (
            <Alert className="mb-3" title="No answer">
              {error}
            </Alert>
          )}
          <label htmlFor="assistant-question" className="sr-only">
            Your question
          </label>
          <div className="flex items-end gap-2">
            <Textarea
              id="assistant-question"
              rows={2}
              maxLength={4000}
              placeholder={
                enabled ? 'Ask a question… (Enter to send, Shift+Enter for a new line)' : ''
              }
              value={question}
              disabled={!enabled}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault()
                  void ask(question)
                }
              }}
              className="min-h-[2.75rem] resize-none"
            />
            {busy ? (
              <Button variant="ghost" className="w-auto" onClick={() => abort.current?.abort()}>
                Stop
              </Button>
            ) : (
              <Button type="submit" className="w-auto" disabled={!enabled || !question.trim()}>
                Ask
              </Button>
            )}
          </div>
        </form>
      </Card>

      <p className="mt-3 text-xs text-faint">
        This chat stays in this browser tab only: nothing is saved on the server, and closing the
        tab or <b className="font-medium">Clear chat</b> deletes it.
        {status.data?.enabled &&
          ` Answers come from ${status.data.documents.length} project docs via ${status.data.model} and can be wrong, so check the source doc.`}
      </p>
    </>
  )
}
