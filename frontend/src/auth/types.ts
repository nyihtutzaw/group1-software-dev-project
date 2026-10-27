// Mirrors backend/app/auth/models.py (Role) and schemas.py (UserOut).
export type Role = 'developer' | 'verifier' | 'registry_staff' | 'buyer' | 'admin'

export const ROLE_LABELS: Record<Role, string> = {
  developer: 'Project developer',
  verifier: 'Independent verifier',
  registry_staff: 'Registry staff',
  buyer: 'Buyer',
  admin: 'Registry admin',
}

export type User = {
  id: number
  email: string
  full_name: string
  organization: string | null
  role: Role
}

export type DemoAccount = Pick<User, 'email' | 'full_name' | 'role'>
