import { FeaturePlaceholder } from '@/components/FeaturePlaceholder'
import { PageHeader } from '@/components/ui'

export function UsersPage() {
  return (
    <>
      <PageHeader title="Users" subtitle="Accounts and roles" />
      <FeaturePlaceholder feature="F5" icon="users" title="User management">
        Create users, assign one of the five roles and deactivate accounts. Separation of duties is
        enforced on the server.
      </FeaturePlaceholder>
    </>
  )
}
