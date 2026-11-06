import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/AuthProvider'
import { request } from '../api/client'
import { AdminPaymentsPage } from './AdminPaymentsPage'
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
vi.mock('../api/client', async (original) => ({ ...await original<typeof import('../api/client')>(), request: vi.fn() }))
const id = '11111111-1111-4111-8111-111111111111', owner = '22222222-2222-4222-8222-222222222222'
function session(role = 'admin', verified = true, account = owner, loading = false) { vi.mocked(useAuth).mockReturnValue({ user: { id: account, role, has_verified_email: verified, first_name: 'Test', last_name: null, email: 'admin@example.test' }, loading, error: null, signIn: vi.fn(), signOut: vi.fn(), acceptSession: vi.fn(), clearSession: vi.fn(), updateProfileNames: vi.fn() }) }
const page = () => <MemoryRouter><AdminPaymentsPage /></MemoryRouter>
const detail = () => <MemoryRouter initialEntries={[`/admin/payments/${id}`]}><Routes><Route path="/admin/payments/:id" element={<AdminPaymentsPage detail />} /></Routes></MemoryRouter>
const payment = () => ({ id, order_id: id, order_number: 'WHZ-001', method: 'cod', status: 'pending', amount: '1200.25', gateway_reference: null, paid_at: null, created_at: '2026-11-01T00:00:00Z', currency: 'PKR', order_status: 'delivered', order_updated_at: '2026-11-01T01:00:00Z', can_record_cod_collection: true, collection_blockers: [], collection_recorded_by: null })
beforeEach(() => { vi.mocked(request).mockReset(); session(); sessionStorage.clear() })
it.each([['customer', true], ['seller', true], ['Admin', true], ['admin', false]] as const)('blocks payment reads for %s verified=%s', (role, verified) => { session(role, verified); render(page()); expect(request).not.toHaveBeenCalled() })
it('waits for restoration', () => { session('admin', true, owner, true); render(page()); expect(request).not.toHaveBeenCalled() })
it('does not render malformed private payment data', async () => { vi.mocked(request).mockResolvedValue({ data: [{ order_number: 'Unverified private payment' }] }); render(page()); await screen.findByRole('alert'); expect(screen.queryByText('Unverified private payment')).not.toBeInTheDocument() })
it('aborts old owner reads and discards their private results', async () => {
  let finish: (value: unknown) => void = () => {}; vi.mocked(request).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve })).mockResolvedValue({ data: [], total: 0, page: 1, per_page: 25, total_pages: 1 })
  const view = render(page()); await waitFor(() => expect(request).toHaveBeenCalledTimes(1)); session('admin', true, id); view.rerender(page()); await screen.findByText('No payments on this page'); expect(vi.mocked(request).mock.calls[0][1]?.signal?.aborted).toBe(true)
  await act(async () => finish({ data: [payment()], total: 1, page: 1, per_page: 25, total_pages: 1 })); expect(screen.queryByText('WHZ-001')).not.toBeInTheDocument()
})
it('does not send an old admin collection after owner changes during preflight', async () => {
  let finish: (value: unknown) => void = () => {}, reads = 0
  vi.mocked(request).mockImplementation(() => { if (++reads === 2) return new Promise((resolve) => { finish = resolve }); return Promise.resolve(payment()) })
  const view = render(detail()); await screen.findByRole('button', { name: 'Review cash collection' }); fireEvent.change(screen.getByLabelText('Collection receipt reference'), { target: { value: 'RECEIPT-001' } }); fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Review cash collection' })); fireEvent.click(screen.getByRole('button', { name: 'Confirm cash collection' })); await waitFor(() => expect(reads).toBe(2)); session('admin', true, id); view.rerender(detail()); await waitFor(() => expect(reads).toBe(3)); await act(async () => finish(payment())); expect(vi.mocked(request).mock.calls.some(([, options]) => options?.method === 'POST')).toBe(false); expect(sessionStorage.length).toBe(0)
})
