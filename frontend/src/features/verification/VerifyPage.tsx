import { FeaturePlaceholder } from '@/components/FeaturePlaceholder'
import { PageHeader } from '@/components/ui'

export function VerifyPage() {
  return (
    <>
      <PageHeader title="Verification queue" subtitle="Projects assigned to you for review" />
      <FeaturePlaceholder feature="F3" icon="verify" title="Verification queue">
        Assigned projects with due dates and overdue flags; the structured checklist; sign-off
        approved by a different registry staff member (maker-checker).
      </FeaturePlaceholder>
    </>
  )
}
