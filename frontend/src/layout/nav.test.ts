import { describe, expect, it } from 'vitest'

import { navFor } from './nav'

const ids = (role: Parameters<typeof navFor>[0]) => navFor(role).map((item) => item.id)

describe('navFor', () => {
  it('shows only the public registry when signed out', () => {
    expect(ids(null)).toEqual(['registry'])
  })

  it('gives developers submission and map, but not verification', () => {
    expect(ids('developer')).toEqual(['home', 'submit', 'map', 'registry'])
  })

  it('gives buyers the registry and the ledger', () => {
    expect(ids('buyer')).toEqual(['home', 'registry', 'ledger'])
  })

  it('gives admins user management', () => {
    expect(ids('admin')).toContain('users')
  })
})
