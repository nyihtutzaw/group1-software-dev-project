import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { ROLE_LABELS, type Role } from '@/auth/types'
import {
  Alert,
  Card,
  EmptyState,
  Icon,
  PageHeader,
  SectionHeader,
  StatusChip,
} from '@/components/ui'
import { NAV_GROUPS, NAV_ITEMS, START_PAGE, type NavItem } from '@/layout/nav'

import { type EndpointAccess, useAccessMatrix } from './access-api'

const ROLES: Role[] = ['developer', 'verifier', 'registry_staff', 'buyer', 'admin']

const SHORT_LABELS: Record<Role, string> = {
  developer: 'Developer',
  verifier: 'Verifier',
  registry_staff: 'Registry staff',
  buyer: 'Buyer',
  admin: 'Admin',
}

const ROLE_DUTIES: Record<Role, string> = {
  developer: 'Registers projects, their land boundaries and evidence',
  verifier: 'Reviews assigned projects and submits verification reports',
  registry_staff: 'Assigns verifiers, decides on reports, issues credits, grants buyer access',
  buyer: 'Traces credits to their evidence and retires holdings',
  admin: 'Manages user accounts; has every staff permission',
}

const th = 'px-3 py-2.5 text-left text-xs font-medium whitespace-nowrap text-faint'
const td = 'border-t border-line px-3 py-2.5 align-top'

function pageLabel(item: NavItem) {
  return item.group ? `${NAV_GROUPS[item.group].label} › ${item.label}` : item.label
}

function pageLabelFor(path: string) {
  const item = NAV_ITEMS.find((i) => i.path === path)
  return item ? pageLabel(item) : path
}

/** One matrix cell: a tick when the role has access, a dash when it does not. */
function Cell({ allowed }: { allowed: boolean }) {
  return (
    <td className={`${td} text-center`}>
      {allowed ? (
        <>
          <Icon name="check" strokeWidth={2.4} className="inline size-4 text-ok" />
          <span className="sr-only">Allowed</span>
        </>
      ) : (
        <>
          <span aria-hidden="true" className="text-faint">
            —
          </span>
          <span className="sr-only">No access</span>
        </>
      )}
    </td>
  )
}

function Table({ label, head, children }: { label: string; head: ReactNode; children: ReactNode }) {
  return (
    <Card className="overflow-x-auto">
      <table aria-label={label} className="w-full border-collapse text-sm">
        <thead className="bg-surface-2">
          <tr>{head}</tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </Card>
  )
}

const roleHeads = ROLES.map((role) => (
  <th key={role} scope="col" className={`${th} text-center`}>
    {SHORT_LABELS[role]}
  </th>
))

function RolesTable() {
  return (
    <Table
      label="Roles"
      head={
        <>
          <th scope="col" className={th}>
            Role
          </th>
          <th scope="col" className={th}>
            Responsibilities
          </th>
          <th scope="col" className={th}>
            Starts on
          </th>
        </>
      }
    >
      {ROLES.map((role) => (
        <tr key={role}>
          <th scope="row" className={`${td} text-left font-medium text-ink`}>
            {ROLE_LABELS[role]}
            <span className="block font-mono text-xs font-normal text-faint">{role}</span>
          </th>
          <td className={`${td} min-w-56 text-muted`}>{ROLE_DUTIES[role]}</td>
          <td className={`${td} whitespace-nowrap text-muted`}>{pageLabelFor(START_PAGE[role])}</td>
        </tr>
      ))}
    </Table>
  )
}

function PageAccessTable() {
  return (
    <Table
      label="Page access"
      head={
        <>
          <th scope="col" className={th}>
            Page
          </th>
          <th scope="col" className={`${th} text-center`}>
            Signed out
          </th>
          {roleHeads}
        </>
      }
    >
      {NAV_ITEMS.map((item) => (
        <tr key={item.id}>
          <th scope="row" className={`${td} text-left font-medium whitespace-nowrap text-ink`}>
            {pageLabel(item)}
            <span className="block font-mono text-xs font-normal text-faint">{item.path}</span>
          </th>
          <Cell allowed={Boolean(item.public)} />
          {ROLES.map((role) => (
            <Cell key={role} allowed={item.roles.includes(role)} />
          ))}
        </tr>
      ))}
    </Table>
  )
}

const ACCESS_CHIPS: Record<EndpointAccess['access'], ReactNode> = {
  public: <StatusChip tone="accent">Public</StatusChip>,
  signed_in: <StatusChip tone="draft">Any signed-in user</StatusChip>,
  roles: null,
}

function ApiAccessTable({ endpoints }: { endpoints: EndpointAccess[] }) {
  const areas = [...new Set(endpoints.map((e) => e.area))]
  return (
    <Table
      label="API access"
      head={
        <>
          <th scope="col" className={th}>
            Endpoint
          </th>
          {roleHeads}
        </>
      }
    >
      {areas.map((area) => (
        <AreaRows key={area} area={area} endpoints={endpoints.filter((e) => e.area === area)} />
      ))}
    </Table>
  )
}

function AreaRows({ area, endpoints }: { area: string; endpoints: EndpointAccess[] }) {
  return (
    <>
      <tr>
        <th
          scope="colgroup"
          colSpan={ROLES.length + 1}
          className="border-t border-line bg-surface-2/60 px-3 py-2 text-left text-xs font-semibold text-muted"
        >
          {area}
        </th>
      </tr>
      {endpoints.map((e) => (
        <tr key={`${e.method} ${e.path}`}>
          <th scope="row" className={`${td} min-w-72 text-left font-normal`}>
            <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-mono text-xs font-semibold text-ink">{e.method}</span>
              <span className="font-mono text-xs break-all text-ink">{e.path}</span>
              {ACCESS_CHIPS[e.access]}
            </span>
            <span className="mt-0.5 block text-xs text-faint">{e.summary}</span>
          </th>
          {ROLES.map((role) => (
            <Cell key={role} allowed={e.roles.includes(role)} />
          ))}
        </tr>
      ))}
    </>
  )
}

function ApiAccess() {
  const matrix = useAccessMatrix()
  if (matrix.isPending) return <p className="text-sm text-faint">Loading API access…</p>
  if (matrix.isError) {
    return <Alert title="Could not load the API access matrix">{matrix.error.message}</Alert>
  }
  if (matrix.data.endpoints.length === 0) {
    return <EmptyState icon="shield" title="No API endpoints found" />
  }
  return <ApiAccessTable endpoints={matrix.data.endpoints} />
}

/** System › Role & Access — the five roles and what each may open and call. Read-only. */
export function RolesAccessPage() {
  return (
    <>
      <PageHeader
        title="Role & Access"
        subtitle="The five roles and which pages and API endpoints each one can use"
      />

      <Alert tone="ok" icon="lock" title="Read-only">
        Access rules are defined in code and change only through a reviewed pull request: page
        access in <code className="font-mono">layout/nav.ts</code>, API access by{' '}
        <code className="font-mono">require_roles</code> on each endpoint. To change someone's role,
        use{' '}
        <Link to="/admin/users" className="font-semibold text-accent hover:underline">
          Users
        </Link>
        .
      </Alert>

      <SectionHeader title="Roles" />
      <RolesTable />

      <SectionHeader title="Page access" />
      <PageAccessTable />

      <SectionHeader title="API access" />
      <p className="mb-3 text-[13px] text-faint">
        Read from the running server. Some endpoints narrow access further by ownership: developers
        reach only their own projects, verifiers only their assigned reviews, buyers only the
        projects they were granted.
      </p>
      <ApiAccess />
    </>
  )
}
