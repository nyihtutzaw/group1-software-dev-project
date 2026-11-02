import { StatusChip } from '@/components/ui'

import type { Credit } from './api'

export function CreditStatus({ status }: { status: Credit['status'] }) {
  return (
    <StatusChip tone={status === 'active' ? 'ok' : status === 'revoked' ? 'warn' : 'draft'}>
      {status}
    </StatusChip>
  )
}
