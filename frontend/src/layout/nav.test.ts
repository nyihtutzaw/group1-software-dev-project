import { describe, expect, it } from 'vitest'

import { isUnder, menuEntries, navFor, navItem } from './nav'

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

  it('gives registry staff and admins buyer access management', () => {
    expect(ids('registry_staff')).toContain('access')
    expect(ids('admin')).toContain('access')
    expect(ids('buyer')).not.toContain('access')
  })

  it('gives admins user management', () => {
    expect(ids('admin')).toContain('users')
  })

  it('gives only admins the System › Role & Access page', () => {
    expect(ids('admin')).toContain('roles-access')
    for (const role of ['developer', 'verifier', 'registry_staff', 'buyer'] as const) {
      expect(ids(role)).not.toContain('roles-access')
    }
  })
})

describe('menuEntries', () => {
  it('collapses grouped items into one System parent menu', () => {
    const entries = menuEntries(navFor('admin'))
    const system = entries.find((e) => e.kind === 'group')
    expect(system).toMatchObject({ kind: 'group', id: 'system', label: 'System' })
    expect(system?.kind === 'group' && system.items.map((i) => i.id)).toEqual(['roles-access'])
    expect(
      entries.filter((e) => e.kind === 'item').map((e) => e.kind === 'item' && e.item.id),
    ).not.toContain('roles-access')
  })

  it('has no System menu for roles without system pages', () => {
    expect(menuEntries(navFor('developer')).every((e) => e.kind === 'item')).toBe(true)
  })
})

describe('isUnder', () => {
  it('matches a page and its sub-pages only', () => {
    const access = navItem('roles-access')
    expect(isUnder(access, '/system/roles-access')).toBe(true)
    expect(isUnder(access, '/system/roles-access/x')).toBe(true)
    expect(isUnder(access, '/system/roles')).toBe(false)
    expect(isUnder(navItem('home'), '/ledger')).toBe(false)
  })
})
