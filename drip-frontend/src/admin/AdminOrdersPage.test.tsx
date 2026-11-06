import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/AuthProvider'
import { request } from '../api/client'
import { AdminOrdersPage } from './AdminOrdersPage'
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
vi.mock('../api/client', async (original) => ({ ...await original<typeof import('../api/client')>(), request: vi.fn() }))
const id = '11111111-1111-4111-8111-111111111111'
const row = { id, order_number: 'Old private order', status: 'processing', customer_name: 'Private Recipient', seller_count: 0, subtotal: '100.25', total: '100.25', commission: '0', payment_method: 'cod', created_at: '2026-10-28T00:00:00Z' }
const empty = { data: [], totals: { total_gmv: '0', total_commission: '0', order_count: 0 }, page: 1, per_page: 25, total: 0, total_pages: 1 }
function session(role = 'admin', verified = true, owner = 'owner-a', loading = false) {
  vi.mocked(useAuth).mockReturnValue({ user: { id: owner, role, has_verified_email: verified, first_name: 'Test', last_name: null, email: 'admin@example.test' }, loading, error: null, signIn: vi.fn(), signOut: vi.fn(), acceptSession: vi.fn(), clearSession: vi.fn(), updateProfileNames: vi.fn() })
}
const page = (url = '/admin/orders') => <MemoryRouter initialEntries={[url]}><AdminOrdersPage /></MemoryRouter>
beforeEach(() => { vi.mocked(request).mockReset(); session() })
it.each([['customer', true], ['seller', true], ['Admin', true], ['admin', false]] as const)('blocks reads for %s verified=%s', (role, verified) => { session(role, verified); render(page()); expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(role === 'admin' ? 'Verify your email' : 'administrator account'); expect(request).not.toHaveBeenCalled() })
it('waits for restoration and rejects invalid URL filters before reading', () => { session('admin', true, 'a', true); const view = render(page()); expect(request).not.toHaveBeenCalled(); view.unmount(); session(); render(page('/admin/orders?seller_id=invalid')); expect(screen.getByRole('alert')).toHaveTextContent('valid seller'); expect(request).not.toHaveBeenCalled() })
it('discards delayed list results from the previous admin owner', async () => {
  let finish: (value: unknown) => void = () => {}; vi.mocked(request).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve })).mockResolvedValue(empty)
  const view = render(page()); await waitFor(() => expect(request).toHaveBeenCalledTimes(1)); session('admin', true, 'owner-b'); view.rerender(page()); await screen.findByText('No orders on this page'); expect(vi.mocked(request).mock.calls[0][1]?.signal?.aborted).toBe(true)
  await act(async () => finish({ ...empty, data: [row], total: 1, totals: { ...empty.totals, order_count: 1 } })); expect(screen.queryByText('Old private order')).not.toBeInTheDocument()
})
it('discards delayed private detail after the admin owner changes', async () => {
  let finish: (value: unknown) => void = () => {}
  const detail = { ...row, discount_amount: '0', shipping_fee: '0', user_id: null, notes: null, address: null, items: [], seller_orders: [] }
  vi.mocked(request).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve })).mockResolvedValue({ ...detail, order_number: 'Current owner order' })
  const component = () => <MemoryRouter initialEntries={[`/admin/orders/${id}`]}><Routes><Route path="/admin/orders/:id" element={<AdminOrdersPage detail />} /></Routes></MemoryRouter>
  const view = render(component()); await waitFor(() => expect(request).toHaveBeenCalledTimes(1)); session('admin', true, 'owner-b'); view.rerender(component()); await screen.findByRole('heading', { name: 'Current owner order' }); await act(async () => finish(detail)); expect(screen.queryByRole('heading', { name: 'Old private order' })).not.toBeInTheDocument(); expect(vi.mocked(request).mock.calls.every(([, options]) => !options?.method || options.method === 'GET')).toBe(true)
})
