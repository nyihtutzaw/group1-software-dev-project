import { useQuery } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'

import { ROLE_LABELS, type DemoAccount } from '@/auth/types'
import { useAuth } from '@/auth/useAuth'
import { Alert, Button, Card, Field, Input, SectionHeader } from '@/components/ui'
import { Brand } from '@/layout/Brand'
import { START_PAGE } from '@/layout/nav'
import { api } from '@/lib/api'

const DEMO_PASSWORD = 'crvr-demo'

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
    <div className="grid min-h-screen place-items-center px-4 py-10">
      <div className="w-full max-w-[400px]">
        <div className="mb-6 flex justify-center">
          <Brand />
        </div>
        <h1 className="mb-1 text-center font-serif text-[29px] font-bold tracking-[-0.015em]">
          Sign in
        </h1>
        <p className="mb-5 text-center text-[13.5px] text-faint">
          Carbon Removal Verification Registry
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

          <Button type="submit" className="mt-3.5" disabled={login.isPending}>
            {login.isPending ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>

        {demo.data && demo.data.length > 0 && (
          <section className="mt-7">
            <SectionHeader title="Demo accounts" action={<span>password {DEMO_PASSWORD}</span>} />
            <Card>
              {demo.data.map((account) => (
                <button
                  key={account.email}
                  type="button"
                  className="flex w-full items-center justify-between gap-3 border-b border-line px-3.5 py-2.5 text-left last:border-b-0 hover:bg-surface-2"
                  onClick={() => signIn({ email: account.email, password: DEMO_PASSWORD })}
                >
                  <span>
                    <b className="block text-sm font-semibold">{account.full_name}</b>
                    <span className="font-mono text-xs text-faint">{account.email}</span>
                  </span>
                  <span className="text-xs font-semibold text-accent">
                    {ROLE_LABELS[account.role]}
                  </span>
                </button>
              ))}
            </Card>
          </section>
        )}
      </div>
    </div>
  )
}
