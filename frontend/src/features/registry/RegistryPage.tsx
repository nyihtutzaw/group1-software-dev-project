import { type FormEvent, useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { useAuth } from '@/auth/useAuth'
import { Alert, Button, Card, EmptyState, Icon, Input, PageHeader } from '@/components/ui'

import { useCredits } from './api'
import { CreditStatus } from './CreditStatus'

const COLS = 'desk:grid-cols-[minmax(0,1.4fr)_minmax(0,1.3fr)_80px_120px_90px_16px]'

export function RegistryPage() {
  const { user } = useAuth()
  // Search and page live in the URL, so Back from a credit returns to the same results
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const page = Math.max(1, Number(params.get('page')) || 1)
  const [input, setInput] = useState(q)
  const credits = useCredits(q, page)

  function go(next: { q?: string; page?: number }) {
    const query = next.q ?? q
    const number = next.page ?? 1
    setParams(
      {
        ...(query ? { q: query } : {}),
        ...(number > 1 ? { page: String(number) } : {}),
      },
      { replace: true },
    )
  }

  function onSearch(event: FormEvent) {
    event.preventDefault()
    go({ q: input.trim(), page: 1 })
  }

  const pages = credits.data
    ? Math.max(1, Math.ceil(credits.data.total / credits.data.page_size))
    : 1

  return (
    <>
      <PageHeader
        title="Public registry"
        subtitle="Every issued credit, traceable to the evidence behind it"
      />
      {user?.role === 'buyer' && (
        <p className="mb-3 text-sm text-muted">Showing projects you are permitted to access.</p>
      )}
      <form onSubmit={onSearch} role="search" className="mb-5 flex items-center gap-2.5">
        <div className="relative min-w-0 flex-1">
          <Icon
            name="search"
            strokeWidth={2}
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-faint"
          />
          <Input
            aria-label="Search project, serial or country"
            value={input}
            maxLength={200}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Search project, serial or country"
            className="pl-9"
          />
        </div>
        <div className="w-24 shrink-0">
          <Button type="submit">Search</Button>
        </div>
      </form>

      <section aria-label="Registry results" aria-busy={credits.isFetching}>
        {credits.isPending && <p role="status">Loading credits…</p>}
        {credits.isError && (
          <Alert title="Unable to load credits">
            {credits.error.message}
            <Button variant="ghost" className="mt-2" onClick={() => void credits.refetch()}>
              Try again
            </Button>
          </Alert>
        )}
        {credits.data &&
          (credits.data.items.length === 0 ? (
            <EmptyState
              icon="registry"
              title={q ? 'No matching credits' : 'No issued credits available'}
            >
              {q
                ? 'Try another project name, serial or country.'
                : user?.role === 'buyer'
                  ? 'No published credits are available for your permitted projects.'
                  : 'Credits appear here once approved records are published.'}
            </EmptyState>
          ) : (
            <Card className="overflow-hidden">
              <div className="flex items-center justify-between border-b border-line px-4 py-3">
                <b className="text-sm font-semibold">
                  {credits.data.total} {credits.data.total === 1 ? 'result' : 'results'}
                </b>
                <span className="text-xs text-faint">Newest vintage first</span>
              </div>
              <div
                className={`hidden gap-4 border-b border-line bg-surface-2 px-4 py-2.5 text-xs font-medium text-faint desk:grid ${COLS}`}
                aria-hidden="true"
              >
                <span>Project</span>
                <span>Serial</span>
                <span>Vintage</span>
                <span className="text-right">Quantity</span>
                <span>Status</span>
                <span />
              </div>
              <ul>
                {credits.data.items.map((credit) => (
                  <li key={credit.id} className="border-b border-line last:border-b-0">
                    <Link
                      to={`/registry/${credit.id}`}
                      state={{ from: `/registry?${params}` }}
                      className={`grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 px-4 py-3 transition-colors hover:bg-surface-2 ${COLS}`}
                    >
                      <span className="min-w-0">
                        <b className="block truncate text-sm font-semibold">
                          {credit.project_name}
                        </b>
                        <span className="mt-0.5 block truncate text-xs text-faint">
                          {credit.country}
                          <span className="desk:hidden">
                            {' · '}Vintage {credit.vintage} · {credit.quantity.toLocaleString()}{' '}
                            tCO₂e
                          </span>
                        </span>
                      </span>
                      <span className="col-span-2 row-start-2 min-w-0 truncate font-mono text-xs text-muted desk:col-span-1 desk:row-start-auto">
                        {credit.serial}
                      </span>
                      <span className="hidden text-sm tabular-nums desk:block">
                        {credit.vintage}
                      </span>
                      <span className="hidden text-right text-sm tabular-nums desk:block">
                        {credit.quantity.toLocaleString()} t
                      </span>
                      <span className="col-start-2 row-start-1 desk:col-start-auto desk:row-start-auto">
                        <CreditStatus status={credit.status} />
                      </span>
                      <Icon
                        name="chevron"
                        strokeWidth={2}
                        className="hidden size-4 text-faint desk:block"
                      />
                    </Link>
                  </li>
                ))}
              </ul>
              <nav
                aria-label="Registry pagination"
                className="flex items-center justify-between gap-3 border-t border-line px-4 py-3"
              >
                <span className="text-sm whitespace-nowrap text-faint">
                  Page {page} of {pages}
                </span>
                <div className="flex gap-2">
                  <div className="w-24">
                    <Button
                      variant="ghost"
                      disabled={page === 1}
                      onClick={() => go({ page: page - 1 })}
                    >
                      Previous
                    </Button>
                  </div>
                  <div className="w-24">
                    <Button
                      variant="ghost"
                      disabled={page * credits.data.page_size >= credits.data.total}
                      onClick={() => go({ page: page + 1 })}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </nav>
            </Card>
          ))}
      </section>
    </>
  )
}
