import { useState, type FormEvent } from 'react'

import {
  Alert,
  Button,
  ButtonRow,
  Card,
  EmptyState,
  Field,
  Modal,
  PageHeader,
  Select,
  StatusChip,
} from '@/components/ui'

import {
  type AccessGrant,
  useAccessGrants,
  useAccessOptions,
  useGrantAccess,
  useRevokeAccess,
} from './access-api'

/** Registry staff grant buyers access to a project's credits and evidence, or remove it. */
export function AccessPage() {
  const grants = useAccessGrants()
  const options = useAccessOptions()
  const grant = useGrantAccess()
  const revoke = useRevokeAccess()
  const [project, setProject] = useState('')
  const [buyer, setBuyer] = useState('')
  const [granted, setGranted] = useState<AccessGrant | null>(null)
  const [revokeTarget, setRevokeTarget] = useState<AccessGrant | null>(null)

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setGranted(null)
    grant.mutate(
      { project_reference: project, buyer_id: Number(buyer) },
      {
        onSuccess: (created) => {
          setGranted(created)
          setBuyer('')
        },
      },
    )
  }

  function confirmRevoke() {
    if (!revokeTarget) return
    revoke.mutate(
      { project_reference: revokeTarget.project_reference, buyer_id: revokeTarget.buyer_id },
      { onSuccess: () => setRevokeTarget(null) },
    )
  }

  const noOptions =
    options.data && (options.data.projects.length === 0 || options.data.buyers.length === 0)

  return (
    <>
      <PageHeader
        title="Buyer access"
        subtitle="Grant buyers access to a project's credits and evidence · every change is sealed in the ledger"
      />
      <div className="grid items-start gap-4 desk:grid-cols-[minmax(280px,0.8fr)_minmax(0,1.2fr)]">
        <section aria-label="Grant access">
          <h2 className="mb-2 text-sm font-semibold text-ink">Grant access</h2>
          {options.isError && (
            <Alert title="Could not load projects and buyers">{options.error.message}</Alert>
          )}
          {noOptions && (
            <Alert className="mb-3" title="Nothing to grant yet">
              Access needs a project with published credits and an active buyer account.
            </Alert>
          )}
          <Card>
            <form onSubmit={submit}>
              <Field label="Project" htmlFor="access-project">
                <Select
                  id="access-project"
                  value={project}
                  onChange={(event) => setProject(event.target.value)}
                  required
                  disabled={!options.data}
                >
                  <option value="">Choose a project</option>
                  {options.data?.projects.map((item) => (
                    <option key={item.project_reference} value={item.project_reference}>
                      {item.project_name} ({item.project_reference})
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Buyer" htmlFor="access-buyer">
                <Select
                  id="access-buyer"
                  value={buyer}
                  onChange={(event) => setBuyer(event.target.value)}
                  required
                  disabled={!options.data}
                >
                  <option value="">Choose a buyer</option>
                  {options.data?.buyers.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.full_name} · {item.email}
                    </option>
                  ))}
                </Select>
              </Field>
              <div className="px-4 pb-4">
                <Button type="submit" disabled={grant.isPending || !options.data}>
                  {grant.isPending ? 'Granting…' : 'Grant access'}
                </Button>
              </div>
            </form>
          </Card>
          {grant.isError && (
            <Alert className="mt-3" title="Could not grant access">
              {grant.error.message}
            </Alert>
          )}
          {granted && (
            <Alert className="mt-3" tone="ok" title="Access granted">
              {granted.buyer_name} can now see {granted.project_name ?? granted.project_reference}{' '}
              the next time they open the registry.
            </Alert>
          )}
        </section>

        <section aria-label="Current access">
          <h2 className="mb-2 text-sm font-semibold text-ink">Current access</h2>
          {grants.isPending && (
            <Card className="p-6 text-center text-sm text-muted">Loading access grants…</Card>
          )}
          {grants.isError && (
            <Alert title="Could not load access grants">
              {grants.error.message}
              <Button variant="ghost" className="mt-2" onClick={() => void grants.refetch()}>
                Try again
              </Button>
            </Alert>
          )}
          {grants.data?.length === 0 && (
            <EmptyState icon="lock" title="No buyer access granted">
              Buyers only see the projects they are granted here.
            </EmptyState>
          )}
          {!!grants.data?.length && (
            <Card className="overflow-hidden">
              <ul>
                {grants.data.map((item) => (
                  <li
                    key={`${item.project_reference}-${item.buyer_id}`}
                    className="grid gap-3 border-b border-line p-4 last:border-b-0 desk:grid-cols-[minmax(0,1fr)_auto] desk:items-center"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <b className="truncate text-sm font-semibold text-ink">
                          {item.project_name ?? 'Unpublished project'}
                        </b>
                        <span className="font-mono text-xs text-faint">
                          {item.project_reference}
                        </span>
                        {!item.buyer_active && <StatusChip tone="draft">Buyer inactive</StatusChip>}
                      </div>
                      <p className="mt-0.5 truncate text-sm text-muted">
                        {item.buyer_name} · {item.buyer_email}
                      </p>
                    </div>
                    <Button
                      className="w-auto px-3 py-2 text-xs"
                      variant="danger"
                      aria-label={`Revoke ${item.buyer_email} from ${item.project_reference}`}
                      disabled={revoke.isPending}
                      onClick={() => setRevokeTarget(item)}
                    >
                      Revoke
                    </Button>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </section>
      </div>

      <Modal
        open={revokeTarget !== null}
        title="Revoke access?"
        onClose={() => setRevokeTarget(null)}
      >
        {revokeTarget && (
          <>
            <p className="text-sm text-muted">
              {revokeTarget.buyer_name} will no longer see{' '}
              {revokeTarget.project_name ?? revokeTarget.project_reference} or its evidence. You can
              grant access again later.
            </p>
            {revoke.isError && (
              <Alert className="mt-3" title="Could not revoke access">
                {revoke.error.message}
              </Alert>
            )}
            <ButtonRow>
              <Button variant="ghost" onClick={() => setRevokeTarget(null)}>
                Cancel
              </Button>
              <Button variant="danger" disabled={revoke.isPending} onClick={confirmRevoke}>
                {revoke.isPending ? 'Revoking…' : 'Revoke access'}
              </Button>
            </ButtonRow>
          </>
        )}
      </Modal>
    </>
  )
}
