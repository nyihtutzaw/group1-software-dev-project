import { Alert } from '@/components/ui'

import { useChangeNotes } from './api'

const TITLE = {
  changes_requested: 'changes requested',
  rejected: 'verification rejected',
} as const

/** Notes sent back to the developer: a verifier's request for changes or a staff rejection. */
export function DeveloperNotes() {
  const notes = useChangeNotes(true)
  if (!notes.data?.length) return null
  return (
    <div className="mb-4 grid gap-2.5">
      {notes.data.map((item) => (
        <Alert key={item.project_id} title={`${item.project_code} · ${TITLE[item.kind]}`}>
          {item.note}
        </Alert>
      ))}
    </div>
  )
}
