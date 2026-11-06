import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/AuthProvider'
import { request } from '../api/client'
import { AdminRefundsPage } from './AdminRefundsPage'
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
vi.mock('../api/client', async (original) => ({ ...await original<typeof import('../api/client')>(), request: vi.fn() }))
const id = '11111111-1111-4111-8111-111111111111', owner = '22222222-2222-4222-8222-222222222222'
function session(role = 'admin', verified = true, account = owner, loading = false) { vi.mocked(useAuth).mockReturnValue({ user: { id: account, role, has_verified_email: verified, first_name: 'Test', last_name: null, email: 'admin@example.test' }, loading, error: null, signIn: vi.fn(), signOut: vi.fn(), acceptSession: vi.fn(), clearSession: vi.fn(), updateProfileNames: vi.fn() }) }
const list = () => <MemoryRouter><AdminRefundsPage /></MemoryRouter>
const payment = () => <MemoryRouter initialEntries={[`/admin/payments/${id}/refunds`]}><Routes><Route path="/admin/payments/:id/refunds" element={<AdminRefundsPage mode="payment" />} /></Routes></MemoryRouter>
const history = () => ({ payment_id: id, order_id: id, order_number: 'WHZ-001', payment_status: 'completed', payment_method: 'cod', payment_amount: '2600', currency: 'PKR', pending_refund_amount: '0', completed_refund_amount: '0', reserved_refund_amount: '0', remaining_refundable_amount: '2600', can_request_refund: true, refunds: [] })
beforeEach(() => { vi.mocked(request).mockReset(); session(); sessionStorage.clear() })
it.each([['customer', true], ['seller', true], ['Admin', true], ['admin', false]] as const)('blocks refund reads for %s verified=%s', (role, verified) => { session(role, verified); render(list()); expect(request).not.toHaveBeenCalled() })
it('waits for session restoration', () => { session('admin', true, owner, true); render(list()); expect(request).not.toHaveBeenCalled() })
it('does not display malformed private refund data', async () => { vi.mocked(request).mockResolvedValue({ data: [{ reason: 'Unverified private reason' }] }); render(list()); await screen.findByRole('alert'); expect(screen.queryByText('Unverified private reason')).not.toBeInTheDocument() })
it('discards old owner list reads', async () => {
  let finish: (value: unknown) => void = () => {}; vi.mocked(request).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve })).mockResolvedValue({ data: [], total: 0, page: 1, per_page: 25, total_pages: 1 })
  const view = render(list()); await waitFor(() => expect(request).toHaveBeenCalledTimes(1)); session('admin', true, id); view.rerender(list()); await screen.findByText('No refunds on this page'); expect(vi.mocked(request).mock.calls[0][1]?.signal?.aborted).toBe(true); await act(async () => finish({ data: [], total: 0, page: 1, per_page: 25, total_pages: 1 })); expect(screen.queryByText('Unverified private reason')).not.toBeInTheDocument()
})
it('never sends an old admin request after ownership changes during preflight', async () => {
  let finish: (value: unknown) => void = () => {}, reads = 0; vi.mocked(request).mockImplementation(() => { if (++reads === 2) return new Promise((resolve) => { finish = resolve }); return Promise.resolve(history()) })
  const view = render(payment()); await screen.findByRole('button', { name: 'Review refund request' }); fireEvent.change(screen.getByLabelText('Refund amount (PKR)'), { target: { value: '500' } }); fireEvent.change(screen.getByLabelText('Refund reason'), { target: { value: 'Customer refund' } }); fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Review refund request' })); fireEvent.click(screen.getByRole('button', { name: 'Confirm pending refund request' })); await waitFor(() => expect(reads).toBe(2)); session('admin', true, id); view.rerender(payment()); await waitFor(() => expect(reads).toBe(3)); await act(async () => finish(history())); expect(vi.mocked(request).mock.calls.some(([, options]) => options?.method === 'POST')).toBe(false); expect(sessionStorage.length).toBe(0)
})
