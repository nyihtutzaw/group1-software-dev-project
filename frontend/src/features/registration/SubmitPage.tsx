import { FeaturePlaceholder } from '@/components/FeaturePlaceholder'
import { PageHeader } from '@/components/ui'

export function SubmitPage() {
  return (
    <>
      <PageHeader title="Register a project" subtitle="Step-by-step project details and evidence" />
      <FeaturePlaceholder feature="F1" icon="submit" title="Project registration form">
        A guided multi-step form — project identity, methodology, crediting period, area and
        baseline — then evidence upload. Files are sealed on submission.
      </FeaturePlaceholder>
    </>
  )
}
