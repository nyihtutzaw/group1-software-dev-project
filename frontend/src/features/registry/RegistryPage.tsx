import { FeaturePlaceholder } from '@/components/FeaturePlaceholder'
import { PageHeader } from '@/components/ui'

export function RegistryPage() {
  return (
    <>
      <PageHeader
        title="Public registry"
        subtitle="Every issued credit, traceable to the evidence behind it"
      />
      <FeaturePlaceholder feature="F4" icon="registry" title="Public registry">
        Search issued credits and open one to see its full traceability: serial, vintage, project,
        verifier, sign-off date and status.
      </FeaturePlaceholder>
    </>
  )
}
