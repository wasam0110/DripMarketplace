import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/AuthProvider'
import { request } from '../api/client'
import { AdminSellersPage } from './AdminSellersPage'
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
vi.mock('../api/client', async (original) => ({ ...await original<typeof import('../api/client')>(), request: vi.fn() }))
function session(role = 'admin', verified = true, id = 'owner-a', loading = false) {
  vi.mocked(useAuth).mockReturnValue({ user: { id, role, has_verified_email: verified, first_name: 'Test', last_name: null, email: 'admin@example.test' }, loading, error: null, signIn: vi.fn(), signOut: vi.fn(), acceptSession: vi.fn(), clearSession: vi.fn(), updateProfileNames: vi.fn() })
}
const page = () => <MemoryRouter><AdminSellersPage /></MemoryRouter>
beforeEach(() => { vi.mocked(request).mockReset(); session(); sessionStorage.clear() })
it.each([['seller', true], ['customer', true], ['Admin', true], ['admin', false]] as const)('does not read private sellers for %s verified=%s', (role, verified) => {
  session(role, verified); render(page()); expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(role === 'admin' ? 'Verify your email' : 'administrator account'); expect(request).not.toHaveBeenCalled()
})
it('does not read before session restoration completes', () => {
  session('admin', true, 'owner-a', true); render(page()); expect(screen.getByRole('status')).toHaveTextContent('Checking your session'); expect(request).not.toHaveBeenCalled()
})
it('discards private results when the owner changes and ignores the old request', async () => {
  let finish: (data: unknown) => void = () => {}
  vi.mocked(request).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve })).mockResolvedValue({ data: [], total: 0, page: 1, per_page: 25, total_pages: 1 })
  const view = render(page()); await waitFor(() => expect(request).toHaveBeenCalledTimes(1))
  session('admin', true, 'owner-b'); view.rerender(page()); await screen.findByText('No sellers on this page')
  expect(vi.mocked(request).mock.calls[0][1]?.signal?.aborted).toBe(true)
  await act(async () => finish({ data: [{ id: '11111111-1111-4111-8111-111111111111', brand_name: 'Old private label', status: 'pending_approval', slots_used: 1, total_slots: 5, product_count: 1, total_gmv: '1000', platform_cut: '150', available_balance: '500', joined_at: '2026-10-28T10:00:00Z' }], total: 1, page: 1, per_page: 25, total_pages: 1 }))
  expect(screen.queryByText('Old private label')).not.toBeInTheDocument()
  expect(request).toHaveBeenCalledWith(expect.stringContaining('/admin/sellers?'), expect.objectContaining({ authenticated: true, cache: 'no-store' }))
})
it('removes private sellers immediately when the account role changes', async () => {
  vi.mocked(request).mockResolvedValue({ data: [], total: 0, page: 1, per_page: 25, total_pages: 1 })
  const view = render(page()); await screen.findByText('No sellers on this page')
  session('customer'); view.rerender(page()); expect(screen.queryByText('No sellers on this page')).not.toBeInTheDocument(); expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('administrator account')
})
