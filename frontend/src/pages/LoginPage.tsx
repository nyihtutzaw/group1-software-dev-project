import { useQuery } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'

import { ROLE_LABELS, type DemoAccount } from '@/auth/types'
import { useAuth } from '@/auth/useAuth'
import {
  Alert,
  Button,
  Card,
  Field,
  Icon,
  type IconName,
  Input,
  SectionHeader,
} from '@/components/ui'
import { Brand } from '@/layout/Brand'
import { START_PAGE } from '@/layout/nav'
import { ThemeToggle } from '@/layout/ThemeToggle'
import { api } from '@/lib/api'

const DEMO_PASSWORD = 'crvr-demo'

const HIGHLIGHTS: [IconName, string][] = [
  ['map', 'Boundaries checked for overlaps with every registered project'],
  ['verify', 'Independent verification, approved by separate registry staff'],
  ['ledger', 'A tamper-evident ledger of every decision'],
]

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const demo = useQuery({
    queryKey: ['auth', 'demo-accounts'],
    queryFn: () => api.get<DemoAccount[]>('/auth/demo-accounts'),
  })

  if (user) return <Navigate to={from ?? START_PAGE[user.role]} replace />

  const signIn = (credentials: { email: string; password: string }) =>
    login.mutate(credentials, {
      onSuccess: (u) => navigate(from ?? START_PAGE[u.role], { replace: true }),
    })

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    signIn({ email, password })
  }

  return (
    <div className="grid min-h-screen desk:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <aside className="relative hidden flex-col justify-between overflow-hidden border-r border-line bg-accent-soft p-10 desk:flex">
        <Brand />
        <div className="max-w-md">
          <h2 className="text-[28px] leading-tight font-semibold tracking-[-0.02em] text-ink">
            Every credit traced back to its evidence.
          </h2>
          <p className="mt-3 text-[15px] text-muted">
            Register carbon-removal projects, verify them under maker-checker review and publish
            credits buyers can trust.
          </p>
          <ul className="mt-8 grid gap-3 text-sm text-muted">
            {HIGHLIGHTS.map(([icon, text]) => (
              <li key={text} className="flex items-center gap-3">
                <span className="grid size-8 flex-none place-items-center rounded-lg bg-surface text-accent shadow-card">
                  <Icon name={icon} className="size-4" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-faint">ITCS514 · Mahidol University</p>
      </aside>

      <main className="relative flex flex-col items-center justify-center px-4 py-12">
        <ThemeToggle className="absolute top-4 right-4" />
        <div className="w-full max-w-[400px]">
          <div className="mb-8 flex desk:hidden">
            <Brand />
          </div>
          <h1 className="text-[26px] leading-tight font-semibold tracking-[-0.02em]">Sign in</h1>
          <p className="mt-1 mb-6 text-sm text-faint">
            Welcome back to the Carbon Removal Verification Registry.
          </p>

          <form onSubmit={onSubmit}>
            <Card>
              <Field label="Email" htmlFor="email">
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </Field>
              <Field label="Password" htmlFor="password">
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
            </Card>

            {login.isError && (
              <Alert className="mt-3" title="Could not sign in">
                {login.error.message}
              </Alert>
            )}

            <Button type="submit" className="mt-4" disabled={login.isPending}>
              {login.isPending ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          {demo.data && demo.data.length > 0 && (
            <section className="mt-8">
              <SectionHeader
                title="Demo accounts"
                action={<span className="font-normal text-faint">password {DEMO_PASSWORD}</span>}
              />
              <Card className="overflow-hidden">
                {demo.data.map((account) => (
                  <button
                    key={account.email}
                    type="button"
                    className="flex w-full items-center justify-between gap-3 border-b border-line px-4 py-2.5 text-left transition-colors last:border-b-0 hover:bg-surface-2"
                    onClick={() => signIn({ email: account.email, password: DEMO_PASSWORD })}
                  >
                    <span className="min-w-0">
                      <b className="block truncate text-sm font-semibold">{account.full_name}</b>
                      <span className="block truncate text-xs text-faint">{account.email}</span>
                    </span>
                    <span className="flex-none rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent">
                      {ROLE_LABELS[account.role]}
                    </span>
                  </button>
                ))}
              </Card>
            </section>
          )}
        </div>
      </main>
    </div>
  )
}
