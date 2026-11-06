import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { PortalPage } from './PortalPage'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
vi.mock('../seller/SellerStatus', () => ({ SellerStatus: () => <div>Seller status boundary</div> }))
const profile = (role: string) => ({
  id: 'owner', role, email: 'owner@example.test', first_name: 'Ayesha',
  last_name: 'Khan', has_verified_email: true,
})
function session(overrides: Partial<ReturnType<typeof useAuth>> = {}) {
  vi.mocked(useAuth).mockReturnValue({
    user: null, loading: false, error: null,
    signIn: vi.fn(), signOut: vi.fn(), acceptSession: vi.fn(),
    clearSession: vi.fn(), updateProfileNames: vi.fn(), ...overrides,
  })
}
beforeEach(() => session())
const page = (role: 'seller' | 'admin') => <MemoryRouter><PortalPage role={role} /></MemoryRouter>

it.each([
  ['customer', '/account'], ['seller', '/seller'], ['admin', '/admin'],
  ['superadmin', '/account'], ['Admin', '/account'], ['', '/account'],
  ['https://other.example', '/account'], [undefined, '/account'],
])('maps only exact supported role %s to a fixed destination', (role, destination) => {
  expect(accountDestination(role)).toBe(destination)
})

it.each(['seller', 'admin'] as const)('shows only the matching %s workspace', (role) => {
  session({ user: profile(role) })
  render(page(role))
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(`${role === 'seller' ? 'Seller' : 'Admin'} workspace`)
  expect(screen.getByRole('link', { name: 'Account settings and sign out' })).toHaveAttribute('href', '/account')
  expect(screen.getByText(/No operational totals or actions/)).toBeInTheDocument()
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})

it.each(['seller', 'admin'] as const)('waits for session restoration before rendering %s details', (role) => {
  session({ user: profile(role), loading: true })
  render(page(role))
  expect(screen.getByRole('status')).toHaveTextContent('Restoring your account')
  expect(screen.queryByText('owner@example.test')).not.toBeInTheDocument()
})

it.each(['seller', 'admin'] as const)('requires a session for %s', (role) => {
  render(page(role))
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Sign in to your workspace')
  expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login')
})

it.each([
  ['seller', 'customer'], ['admin', 'customer'], ['seller', 'admin'],
  ['admin', 'seller'], ['admin', 'superadmin'], ['seller', 'unknown'],
] as const)('denies %s workspace to role %s without implying hierarchy', (workspace, role) => {
  session({ user: profile(role) })
  render(page(workspace))
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('not available to your account')
  expect(screen.getByRole('link', { name: 'Return to your workspace' })).toHaveAttribute('href', accountDestination(role))
  expect(screen.queryByText('owner@example.test')).not.toBeInTheDocument()
})

it('does not show cached account details after a restoration failure', () => {
  session({ user: profile('seller'), error: 'Session unavailable.' })
  render(page('seller'))
  expect(screen.getByRole('alert')).toHaveTextContent('Session unavailable.')
  expect(screen.queryByText('owner@example.test')).not.toBeInTheDocument()
})

it('removes the workspace when the session is cleared or changes role', () => {
  session({ user: profile('admin') })
  const view = render(page('admin'))
  session({ user: profile('customer') })
  view.rerender(page('admin'))
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('not available')
  session()
  view.rerender(page('admin'))
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Sign in to your workspace')
})

it('links verified admins to seller reviews but not unverified admins', () => {
  session({ user: profile('admin') })
  const view = render(page('admin'))
  expect(screen.getByRole('link', { name: 'Review seller applications' })).toHaveAttribute('href', '/admin/sellers')
  expect(screen.getByRole('link', { name: 'Moderate products' })).toHaveAttribute('href', '/admin/products')
  expect(screen.getByRole('link', { name: 'Moderate customer reviews' })).toHaveAttribute('href', '/admin/reviews')
  expect(screen.getByRole('link', { name: 'Manage banners' })).toHaveAttribute('href', '/admin/content')
  expect(screen.getByRole('link', { name: 'Inspect orders' })).toHaveAttribute('href', '/admin/orders')
  expect(screen.getByRole('link', { name: 'Review COD queue' })).toHaveAttribute('href', '/admin/cod')
  expect(screen.getByRole('link', { name: 'Inspect payments and COD collection' })).toHaveAttribute('href', '/admin/payments')
  expect(screen.getByRole('link', { name: 'Inspect refunds and recorded transfers' })).toHaveAttribute('href', '/admin/refunds')
  expect(screen.getByText(/Seller reviews, registration-payment records, product moderation and customer review moderation are connected/)).toBeInTheDocument()
  session({ user: { ...profile('admin'), has_verified_email: false } })
  view.rerender(page('admin'))
  expect(screen.queryByRole('link', { name: 'Review seller applications' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Moderate products' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Moderate customer reviews' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Manage banners' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Inspect orders' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Review COD queue' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Inspect payments and COD collection' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Inspect refunds and recorded transfers' })).not.toBeInTheDocument()
})
