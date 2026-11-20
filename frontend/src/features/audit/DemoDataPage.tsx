import { useCallback, useState } from 'react'

import {
  Alert,
  Button,
  ButtonRow,
  Card,
  Input,
  Modal,
  PageHeader,
  SectionHeader,
  StatTile,
  StatTiles,
} from '@/components/ui'

import { type DemoStart, useDemoData, useResetDemoData } from './demo-data-api'

const STARTS: { id: DemoStart; title: string; what: string; when: string; button: string }[] = [
  {
    id: 'live',
    title: 'Live demo start',
    what: 'The six demo accounts and one neighbouring project, Huai Nam Rin Community Forest, with its boundary. No other projects, no credits, an empty ledger.',
    when: 'Right before the live demo: the presenters register Nam Wa from scratch, exactly as in the demo video.',
    button: 'Reset to live demo start',
  },
  {
    id: 'full',
    title: 'Full sample data',
    what: 'The six demo accounts, sample projects at every stage with boundaries and verifier assignments, and sample credits on the public registry.',
    when: 'After the demo, so people exploring the site see a registry that looks in use.',
    button: 'Reset to full sample data',
  },
]

/**
 * F5 — System › Demo data. An admin wipes the demo server and loads a starting point. The API
 * refuses on a real registry (no demo mode); the page then only explains that.
 */
export function DemoDataPage() {
  const data = useDemoData()
  const reset = useResetDemoData()
  const [chosen, setChosen] = useState<DemoStart | null>(null)
  const [confirm, setConfirm] = useState('')
  const [done, setDone] = useState<DemoStart | null>(null)

  const start = STARTS.find((s) => s.id === chosen)
  // Stable, so the dialog does not re-take focus (from the RESET field) on every keystroke.
  const clearReset = reset.reset
  const close = useCallback(() => {
    setChosen(null)
    setConfirm('')
    clearReset()
  }, [clearReset])

  if (data.isError) {
    return (
      <>
        <PageHeader title="Demo data" />
        <Alert title="Demo data could not be loaded">{data.error.message}</Alert>
      </>
    )
  }
  if (!data.data) return <PageHeader title="Demo data" subtitle="Loading…" />

  const { enabled, counts } = data.data
  return (
    <>
      <PageHeader
        title="Demo data"
        subtitle="Wipe this demo server and start again, e.g. before a presentation"
      />

      {!enabled && (
        <Alert className="mb-3" title="Reset is off on this server" icon="lock">
          This server is not running in demo mode, so its data can never be wiped from here.
        </Alert>
      )}
      {done && (
        <Alert className="mb-3" tone="ok" title="Demo data reset">
          {STARTS.find((s) => s.id === done)?.title} is loaded. The audit ledger starts again, with
          the reset as its first entry.
        </Alert>
      )}

      <StatTiles>
        <StatTile value={counts.users} label="Accounts" />
        <StatTile value={counts.projects} label="Projects" />
        <StatTile value={counts.boundaries} label="Boundaries" />
        <StatTile value={counts.credits} label="Credit batches" />
        <StatTile value={counts.ledger_entries} label="Ledger entries" />
      </StatTiles>

      <SectionHeader title="Start again from" />
      <div className="grid gap-3 md:grid-cols-2">
        {STARTS.map((s) => (
          <Card key={s.id} className="flex flex-col p-4">
            <h3 className="text-base font-semibold text-ink">{s.title}</h3>
            <p className="mt-1.5 text-sm text-muted">{s.what}</p>
            <p className="mt-1.5 text-sm text-faint">{s.when}</p>
            <div className="mt-auto pt-3">
              <Button
                variant="ghost"
                disabled={!enabled}
                onClick={() => {
                  setDone(null)
                  setChosen(s.id)
                }}
              >
                {s.button}
              </Button>
            </div>
          </Card>
        ))}
      </div>
      <p className="mt-3 text-xs text-faint">
        Everyone’s changes are lost, including accounts added on the Users page. Uploaded evidence
        files stay in storage. You stay signed in if you use the demo admin account.
      </p>

      <Modal open={!!start} title={start ? `${start.button}?` : ''} onClose={close}>
        {start && (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              reset.mutate(
                { start: start.id, confirm },
                {
                  onSuccess: () => {
                    setDone(start.id)
                    close()
                  },
                },
              )
            }}
          >
            <p className="text-sm text-muted">
              All projects, evidence records, credits and ledger entries on this server are deleted
              and cannot be brought back. Then: {start.what}
            </p>
            <label
              htmlFor="confirm-reset"
              className="mt-3 mb-1.5 block text-[13px] font-medium text-muted"
            >
              Type RESET to confirm
            </label>
            <Input
              id="confirm-reset"
              autoComplete="off"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
            {reset.isError && (
              <Alert className="mt-3" title="The reset did not run">
                {reset.error.message}
              </Alert>
            )}
            <ButtonRow>
              <Button variant="ghost" onClick={close}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="danger"
                disabled={confirm !== 'RESET' || reset.isPending}
              >
                {reset.isPending ? 'Resetting…' : 'Wipe and reset'}
              </Button>
            </ButtonRow>
          </form>
        )}
      </Modal>
    </>
  )
}
