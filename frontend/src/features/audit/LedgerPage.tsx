import { FeaturePlaceholder } from '@/components/FeaturePlaceholder'
import { PageHeader } from '@/components/ui'

export function LedgerPage() {
  return (
    <>
      <PageHeader
        title="Audit ledger"
        subtitle="Every action, in order · each entry seals the one before it"
      />
      <FeaturePlaceholder feature="F5" icon="ledger" title="Audit ledger">
        Every critical action in order, each entry sealed with the hash of the one before it.
      </FeaturePlaceholder>
    </>
  )
}
