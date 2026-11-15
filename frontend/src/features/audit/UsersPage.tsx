import { useState, type FormEvent } from 'react'

import { useAuth } from '@/auth/useAuth'
import type { Role } from '@/auth/types'
import {
  Alert,
  Button,
  ButtonRow,
  Card,
  EmptyState,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  StatusChip,
} from '@/components/ui'

import {
  type AdminUser,
  type AdminUserCreate,
  useAdminUsers,
  useCreateAdminUser,
  useUpdateAdminUser,
} from './users-api'

const ROLES: { value: Role; label: string }[] = [
  { value: 'developer', label: 'Developer' },
  { value: 'verifier', label: 'Verifier' },
  { value: 'registry_staff', label: 'Registry staff' },
  { value: 'buyer', label: 'Buyer' },
  { value: 'admin', label: 'Admin' },
]

function isRole(value: string): value is Role {
  return ROLES.some((role) => role.value === value)
}

const EMPTY_FORM: AdminUserCreate = {
  email: '',
  full_name: '',
  organization: null,
  role: 'developer',
  initial_password: '',
}

export function UsersPage() {
  const { user: currentUser } = useAuth()
  const users = useAdminUsers()
  const createUser = useCreateAdminUser()
  const updateUser = useUpdateAdminUser()
  const [form, setForm] = useState(EMPTY_FORM)
  const [createdEmail, setCreatedEmail] = useState<string | null>(null)
  const [deactivateTarget, setDeactivateTarget] = useState<AdminUser | null>(null)

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCreatedEmail(null)
    createUser.mutate(form, {
      onSuccess: (created) => {
        setForm(EMPTY_FORM)
        setCreatedEmail(created.email)
      },
    })
  }

  function updateRole(account: AdminUser, role: Role) {
    if (role !== account.role) {
      updateUser.mutate({ userId: account.id, changes: { role } })
    }
  }

  function setActive(account: AdminUser, isActive: boolean) {
    updateUser.mutate({ userId: account.id, changes: { is_active: isActive } })
  }

  return (
    <>
      <PageHeader title="Users" subtitle="Create accounts and manage access by role" />

      {currentUser?.role !== 'admin' ? (
        <Alert title="Admin access required">Only admins can manage user accounts.</Alert>
      ) : (
        <div className="grid items-start gap-4 desk:grid-cols-[minmax(280px,0.8fr)_minmax(0,1.2fr)]">
          <section aria-label="Create user">
            <h2 className="mb-2 text-sm font-semibold text-ink">Create account</h2>
            <Card>
              <form onSubmit={submit}>
                <Field label="Full name" htmlFor="user-full-name">
                  <Input
                    id="user-full-name"
                    autoComplete="name"
                    value={form.full_name}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, full_name: event.target.value }))
                    }
                    required
                    maxLength={120}
                  />
                </Field>
                <Field label="Email" htmlFor="user-email">
                  <Input
                    id="user-email"
                    type="email"
                    autoComplete="email"
                    value={form.email}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, email: event.target.value }))
                    }
                    required
                    maxLength={255}
                  />
                </Field>
                <Field label="Organization (optional)" htmlFor="user-organization">
                  <Input
                    id="user-organization"
                    value={form.organization ?? ''}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        organization: event.target.value || null,
                      }))
                    }
                    maxLength={160}
                  />
                </Field>
                <Field label="Role" htmlFor="user-role">
                  <Select
                    id="user-role"
                    value={form.role}
                    onChange={(event) => {
                      const role = event.target.value
                      if (isRole(role)) {
                        setForm((current) => ({ ...current, role }))
                      }
                    }}
                  >
                    {ROLES.map((role) => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field
                  label="Initial password"
                  htmlFor="user-initial-password"
                  hint="At least 12 characters. Share it with the new user through a secure channel."
                >
                  <Input
                    id="user-initial-password"
                    type="password"
                    autoComplete="new-password"
                    value={form.initial_password}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        initial_password: event.target.value,
                      }))
                    }
                    required
                    minLength={12}
                    maxLength={72}
                  />
                </Field>
                <div className="px-4 pb-4">
                  <Button type="submit" disabled={createUser.isPending}>
                    {createUser.isPending ? 'Creating…' : 'Create user'}
                  </Button>
                </div>
              </form>
            </Card>
            {createUser.isError && (
              <Alert className="mt-3" title="Could not create account">
                {createUser.error.message}
              </Alert>
            )}
            {createdEmail && (
              <Alert className="mt-3" tone="ok" title="Account created">
                {createdEmail} can now sign in. The initial password is not saved in this page.
              </Alert>
            )}
          </section>

          <section aria-label="User accounts">
            <h2 className="mb-2 text-sm font-semibold text-ink">Accounts</h2>
            {users.isPending && (
              <Card className="p-6 text-center text-sm text-muted">Loading accounts…</Card>
            )}
            {users.isError && <Alert title="Could not load accounts">{users.error.message}</Alert>}
            {updateUser.isError && (
              <Alert className="mb-3" title="Could not update account">
                {updateUser.error.message}
              </Alert>
            )}
            {users.data?.length === 0 && (
              <EmptyState icon="users" title="No accounts found">
                Create an account to get started.
              </EmptyState>
            )}
            {!!users.data?.length && (
              <Card className="overflow-hidden">
                <ul>
                  {users.data.map((account) => {
                    const isCurrentUser = account.id === currentUser.id
                    return (
                      <li
                        key={account.id}
                        className="grid gap-3 border-b border-line p-4 last:border-b-0 desk:grid-cols-[minmax(0,1fr)_170px_auto]"
                      >
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <b className="truncate text-sm font-semibold text-ink">
                              {account.full_name}
                            </b>
                            <StatusChip tone={account.is_active ? 'ok' : 'draft'}>
                              {account.is_active ? 'Active' : 'Inactive'}
                            </StatusChip>
                            {isCurrentUser && <span className="text-xs text-faint">You</span>}
                          </div>
                          <p className="mt-0.5 truncate text-sm text-muted">{account.email}</p>
                          {account.organization && (
                            <p className="mt-0.5 truncate text-xs text-faint">
                              {account.organization}
                            </p>
                          )}
                        </div>
                        <Select
                          aria-label={`Role for ${account.email}`}
                          value={account.role}
                          disabled={isCurrentUser || updateUser.isPending}
                          onChange={(event) => {
                            if (isRole(event.target.value)) updateRole(account, event.target.value)
                          }}
                        >
                          {ROLES.map((role) => (
                            <option key={role.value} value={role.value}>
                              {role.label}
                            </option>
                          ))}
                        </Select>
                        <Button
                          className="w-auto px-3 py-2 text-xs"
                          variant={account.is_active ? 'danger' : 'ghost'}
                          disabled={isCurrentUser || updateUser.isPending}
                          onClick={() =>
                            account.is_active
                              ? setDeactivateTarget(account)
                              : setActive(account, true)
                          }
                        >
                          {account.is_active ? 'Deactivate' : 'Reactivate'}
                        </Button>
                      </li>
                    )
                  })}
                </ul>
              </Card>
            )}
          </section>
        </div>
      )}

      <Modal
        open={deactivateTarget !== null}
        title="Deactivate account?"
        onClose={() => setDeactivateTarget(null)}
      >
        {deactivateTarget && (
          <>
            <p className="text-sm text-muted">
              {deactivateTarget.full_name} will no longer be able to sign in. This can be reversed
              by reactivating the account.
            </p>
            {updateUser.isError && (
              <Alert className="mt-3" title="Could not deactivate account">
                {updateUser.error.message}
              </Alert>
            )}
            <ButtonRow>
              <Button variant="ghost" onClick={() => setDeactivateTarget(null)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                disabled={updateUser.isPending}
                onClick={() => {
                  if (deactivateTarget) {
                    updateUser.mutate(
                      { userId: deactivateTarget.id, changes: { is_active: false } },
                      { onSuccess: () => setDeactivateTarget(null) },
                    )
                  }
                }}
              >
                {updateUser.isPending ? 'Deactivating…' : 'Deactivate account'}
              </Button>
            </ButtonRow>
          </>
        )}
      </Modal>
    </>
  )
}
