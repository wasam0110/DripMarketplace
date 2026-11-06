import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/AuthProvider'
import { request } from '../api/client'
import { AdminReviewsPage } from './AdminReviewsPage'
import type { AdminReview } from './reviews'
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
vi.mock('../api/client', async (original) => ({ ...await original<typeof import('../api/client')>(), request: vi.fn() }))
function session(role = 'admin', verified = true, id = 'owner-a', loading = false) {
  vi.mocked(useAuth).mockReturnValue({ user: { id, role, has_verified_email: verified, first_name: 'Test', last_name: null, email: 'admin@example.test' }, loading, error: null, signIn: vi.fn(), signOut: vi.fn(), acceptSession: vi.fn(), clearSession: vi.fn(), updateProfileNames: vi.fn() })
}
const page = (url = '/admin/reviews') => <MemoryRouter initialEntries={[url]}><AdminReviewsPage /></MemoryRouter>
const fixture: AdminReview = { id: '11111111-1111-4111-8111-111111111111', product_id: '22222222-2222-4222-8222-222222222222', user: { id: '33333333-3333-4333-8333-333333333333', first_name: 'Customer', last_name: null, avatar_url: null }, rating: 4, title: 'Old private content', body: 'Review content', status: 'pending', is_verified_purchase: true, helpful_count: 0, unhelpful_count: 0, images: [], admin_note: null, moderated_at: null, created_at: '2026-10-28T00:00:00Z', updated_at: '2026-10-28T00:00:00Z' }
beforeEach(() => { vi.mocked(request).mockReset(); session(); sessionStorage.clear() })
it.each([['customer', true], ['seller', true], ['Admin', true], ['admin', false]] as const)('blocks review reads for %s verified=%s', (role, verified) => {
  session(role, verified); render(page()); expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(role === 'admin' ? 'Verify your email' : 'administrator account'); expect(request).not.toHaveBeenCalled()
})
it('does not read during session restoration or with invalid filters', () => {
  session('admin', true, 'owner-a', true); const view = render(page()); expect(request).not.toHaveBeenCalled(); view.unmount()
  session(); render(page('/admin/reviews?status=invalid')); expect(screen.getByRole('alert')).toHaveTextContent('valid review status'); expect(request).not.toHaveBeenCalled()
})
it('aborts and discards results belonging to the previous admin', async () => {
  let finish: (value: unknown) => void = () => {}
  vi.mocked(request).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve })).mockResolvedValue({ data: [], page: 1, per_page: 25, total: 0 })
  const view = render(page()); await waitFor(() => expect(request).toHaveBeenCalledTimes(1)); session('admin', true, 'owner-b'); view.rerender(page()); await screen.findByText('No reviews on this page')
  expect(vi.mocked(request).mock.calls[0][1]?.signal?.aborted).toBe(true)
  await act(async () => finish({ data: [fixture], page: 1, per_page: 25, total: 1 }))
  expect(screen.queryByText('Old private content')).not.toBeInTheDocument()
})
it('does not send a decision if ownership changes while its preflight is pending', async () => {
  let finish: (value: unknown) => void = () => {}
  vi.mocked(request).mockResolvedValueOnce(fixture).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve })).mockResolvedValue({ ...fixture, title: 'Current owner review' })
  const detail = () => <MemoryRouter initialEntries={[`/admin/reviews/${fixture.id}`]}><Routes><Route path="/admin/reviews/:id" element={<AdminReviewsPage detail />} /></Routes></MemoryRouter>
  const view = render(detail()); fireEvent.click(await screen.findByRole('button', { name: 'Review moderation decision' })); fireEvent.click(screen.getByRole('button', { name: 'Confirm review moderation' }))
  await waitFor(() => expect(request).toHaveBeenCalledTimes(2)); session('admin', true, 'owner-b'); view.rerender(detail()); await screen.findByRole('heading', { name: 'Current owner review' })
  await act(async () => finish(fixture))
  expect(vi.mocked(request).mock.calls.some(([, options]) => options?.method === 'PATCH')).toBe(false)
  expect(sessionStorage.length).toBe(0)
})
