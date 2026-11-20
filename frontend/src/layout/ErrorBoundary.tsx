import { Component, type ErrorInfo, type ReactNode } from 'react'

import { Button, Card, Icon } from '@/components/ui'

type Props = {
  children: ReactNode
  /** When this changes (the page's path), a shown error is cleared so the new page can render. */
  resetKey?: string
  /** Outside the app shell (sign-in, manual): centre the message on the whole screen. */
  fullScreen?: boolean
}

type State = { error: Error | null }

/**
 * Catches a crash while rendering or updating a page and shows a message instead of a blank
 * screen. Inside the app shell it wraps only the page, so the menu keeps working and another page
 * can be opened without a reload.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Page crashed:', error, info.componentStack)
  }

  componentDidUpdate(previous: Props) {
    if (this.state.error && previous.resetKey !== this.props.resetKey)
      this.setState({ error: null })
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children
    const message = (
      <Card role="alert" className="mx-auto max-w-[560px] p-6">
        <div className="mb-3 grid size-11 place-items-center rounded-xl bg-warn-soft text-warn">
          <Icon name="alert" strokeWidth={2} className="size-[22px]" />
        </div>
        <h1 className="text-lg font-semibold text-ink">Something went wrong on this page</h1>
        <p className="mt-1.5 text-sm text-muted">
          Nothing was lost. Try again, or open another page from the menu. If it keeps happening,
          reload the page.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button className="w-auto" onClick={() => this.setState({ error: null })}>
            Try again
          </Button>
          <Button variant="ghost" className="w-auto" onClick={() => window.location.reload()}>
            Reload the page
          </Button>
        </div>
        <details className="mt-4 text-xs text-faint">
          <summary className="cursor-pointer">Technical details</summary>
          <pre className="mt-2 overflow-x-auto font-mono whitespace-pre-wrap">{error.message}</pre>
        </details>
      </Card>
    )
    return this.props.fullScreen ? (
      <div className="grid min-h-screen place-items-center px-4">{message}</div>
    ) : (
      message
    )
  }
}
