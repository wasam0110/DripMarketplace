import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/AuthProvider'
import { request } from '../api/client'
import { AdminCODPage } from './AdminCODPage'
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
vi.mock('../api/client', async (original) => ({ ...await original<typeof import('../api/client')>(), request: vi.fn() }))
function session(role = 'admin', verified = true, id = 'owner-a', loading = false) { vi.mocked(useAuth).mockReturnValue({ user: { id, role, has_verified_email: verified, first_name: 'Test', last_name: null, email: 'admin@example.test' }, loading, error: null, signIn: vi.fn(), signOut: vi.fn(), acceptSession: vi.fn(), clearSession: vi.fn(), updateProfileNames: vi.fn() }) }
const page = () => <MemoryRouter><AdminCODPage /></MemoryRouter>
beforeEach(() => { vi.mocked(request).mockReset(); session(); sessionStorage.clear() })
it.each([['customer', true], ['seller', true], ['Admin', true], ['admin', false]] as const)('blocks COD reads for %s verified=%s', (role, verified) => { session(role, verified); render(page()); expect(request).not.toHaveBeenCalled() })
it('waits for session restoration', () => { session('admin', true, 'a', true); render(page()); expect(request).not.toHaveBeenCalled() })
it('rejects malformed queue receipts before rendering private order cards', async () => { vi.mocked(request).mockResolvedValue([{ order_id: 'bad', order_number: 'Unverified private order' }]); render(page()); await screen.findByRole('alert'); expect(screen.queryByText('Unverified private order')).not.toBeInTheDocument() })
it('aborts and discards valid old queue results when the admin changes', async () => {
  let finish: (value: unknown) => void = () => {}; vi.mocked(request).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve })).mockResolvedValue([])
  const view = render(page()); await waitFor(() => expect(request).toHaveBeenCalledTimes(1)); session('admin', true, 'owner-b'); view.rerender(page()); await screen.findByText('No orders awaiting COD verification'); expect(vi.mocked(request).mock.calls[0][1]?.signal?.aborted).toBe(true)
  await act(async () => finish([{ order_id: '11111111-1111-4111-8111-111111111111', order_number: 'Old private order', customer_name: 'Recipient', customer_phone: '03001234567', total: '100', brand_names: [], placed_at: '2099-01-01T00:00:00Z', expires_at: '2099-01-01T00:30:00Z', updated_at: '2099-01-01T00:00:00Z', minutes_remaining: 30 }]))
  expect(screen.queryByText('Old private order')).not.toBeInTheDocument()
})
it('does not send an action if its admin changes during preflight', async () => {
  const id = '11111111-1111-4111-8111-111111111111', seller = '22222222-2222-4222-8222-222222222222'
  const row = { order_id: id, order_number: 'COD fixture', customer_name: 'Recipient', customer_phone: '03001234567', total: '100', brand_names: ['Brand'], placed_at: '2099-01-01T00:00:00Z', expires_at: '2099-01-01T00:30:00Z', updated_at: '2099-01-01T00:00:00Z', minutes_remaining: 30 }
  const order = { id, order_number: row.order_number, customer_name: row.customer_name, user_id: null, status: 'pending_cod_verification', payment_method: 'cod', subtotal: '100', discount_amount: '0', shipping_fee: '0', total: '100', commission: '0', notes: null, created_at: row.placed_at, address: { recipient_name: row.customer_name, phone: row.customer_phone, street: 'Street', city: 'Lahore', province: 'Punjab', note: null }, items: [{ id, seller_id: seller, product_id: id, variant_id: id, product_name: 'Shirt', variant_label: 'M', quantity: 1, unit_price: '100', subtotal: '100' }], seller_orders: [{ id, seller_id: seller, brand_name: 'Brand', status: 'pending', subtotal: '100', tracking_number: null, courier_name: null, shipped_at: null, delivered_at: null }] }
  let finish: (value: unknown) => void = () => {}, queueReads = 0
  vi.mocked(request).mockImplementation((path) => { if (path === '/admin/cod-queue') { queueReads++; if (queueReads === 2) return new Promise((resolve) => { finish = resolve }); return Promise.resolve([row]) }; return Promise.resolve(order) })
  const detail = () => <MemoryRouter initialEntries={[`/admin/cod/${id}`]}><Routes><Route path="/admin/cod/:id" element={<AdminCODPage detail />} /></Routes></MemoryRouter>
  const view = render(detail()); await screen.findByRole('button', { name: 'Review COD action' }); fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Review COD action' })); fireEvent.click(screen.getByRole('button', { name: 'Confirm COD action' })); await waitFor(() => expect(queueReads).toBe(2)); session('admin', true, 'owner-b'); view.rerender(detail()); await waitFor(() => expect(queueReads).toBe(3)); await act(async () => finish([row])); expect(vi.mocked(request).mock.calls.some(([, options]) => options?.method === 'POST')).toBe(false); expect(sessionStorage.length).toBe(0)
})
