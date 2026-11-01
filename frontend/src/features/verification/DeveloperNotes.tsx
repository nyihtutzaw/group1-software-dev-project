import { Alert } from '@/components/ui'

import { useChangeNotes } from './api'

/** Verifier notes shown to the project developer after a request for changes. */
export function DeveloperNotes() {
  const notes = useChangeNotes(true)
  if (!notes.data?.length) return null
  return (
    <div className="mb-4 grid gap-2.5">
      {notes.data.map((item) => (
        <Alert key={item.project_id} title={`${item.project_code} · changes requested`}>
          {item.note}
        </Alert>
      ))}
    </div>
  )
}
