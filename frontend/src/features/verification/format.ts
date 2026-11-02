import type { AssignmentStatus, QueueItem } from './api'

export function shortDate(value: string) {
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  }).format(new Date(`${value.slice(0, 10)}T00:00:00Z`))
}

export function longDate(value: string) {
  return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(value),
  )
}

/** "4 days overdue", or null when on time. */
export function overdueLabel(item: QueueItem) {
  if (item.days_overdue === 0) return null
  return `${item.days_overdue === 1 ? '1 day' : `${item.days_overdue} days`} overdue`
}

export function dueLabel(item: QueueItem) {
  const overdue = overdueLabel(item)
  return `Due ${shortDate(item.due_date)}${overdue ? ` · ${overdue}` : ''}`
}

/** Queue tabs: where an assignment sits in the maker-checker flow. */
export type QueueGroup = 'open' | 'awaiting' | 'approved'

export function groupOf(status: AssignmentStatus): QueueGroup {
  if (status === 'signed_off') return 'awaiting'
  if (status === 'approved') return 'approved'
  return 'open' // assigned, in review, changes requested, rejected — still with the verifier
}
