import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/AuthProvider'
import { request } from '../api/client'
import { AdminContentPage } from './AdminContentPage'
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
vi.mock('../api/client', async (original) => ({ ...await original<typeof import('../api/client')>(), request: vi.fn() }))
const row = { id: '11111111-1111-4111-8111-111111111111', title: 'Old banner', image_url: 'https://example.test/banner.webp', link_url: '/clothing', position: 'homepage_hero', sort_order: 0, is_active: false, valid_from: null, valid_until: null, created_at: '2026-10-28T00:00:00Z', updated_at: '2026-10-28T00:00:00Z' }
function session(role = 'admin', verified = true, id = 'owner-a', loading = false) {
  vi.mocked(useAuth).mockReturnValue({ user: { id, role, has_verified_email: verified, first_name: 'Test', last_name: null, email: 'admin@example.test' }, loading, error: null, signIn: vi.fn(), signOut: vi.fn(), acceptSession: vi.fn(), clearSession: vi.fn(), updateProfileNames: vi.fn() })
}
const page = () => <MemoryRouter><AdminContentPage /></MemoryRouter>
beforeEach(() => { vi.mocked(request).mockReset(); session(); sessionStorage.clear() })
it.each([['customer', true], ['seller', true], ['Admin', true], ['admin', false]] as const)('blocks content reads for %s verified=%s', (role, verified) => {
  session(role, verified); render(page()); expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(role === 'admin' ? 'Verify your email' : 'administrator account'); expect(request).not.toHaveBeenCalled()
})
it('waits for session restoration', () => { session('admin', true, 'owner-a', true); render(page()); expect(request).not.toHaveBeenCalled() })
it('discards old private results when the admin changes', async () => {
  let finish: (value: unknown) => void = () => {}
  vi.mocked(request).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve })).mockResolvedValue([])
  const view = render(page()); await waitFor(() => expect(request).toHaveBeenCalledTimes(1)); session('admin', true, 'owner-b'); view.rerender(page()); await screen.findByText('No banners yet')
  expect(vi.mocked(request).mock.calls[0][1]?.signal?.aborted).toBe(true); await act(async () => finish([row])); expect(screen.queryByText('Old banner')).not.toBeInTheDocument()
})
it('cannot send an update after an owner change during preflight', async () => {
  let finish: (value: unknown) => void = () => {}
  vi.mocked(request).mockResolvedValueOnce([row]).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve })).mockResolvedValue([{ ...row, title: 'Current owner banner' }])
  const detail = () => <MemoryRouter initialEntries={[`/admin/content/banners/${row.id}`]}><Routes><Route path="/admin/content/banners/:id" element={<AdminContentPage detail />} /></Routes></MemoryRouter>
  const view = render(detail()); fireEvent.change(await screen.findByLabelText('Banner title'), { target: { value: 'Changed title' } }); fireEvent.click(screen.getByRole('button', { name: 'Review banner changes' })); fireEvent.click(screen.getByRole('button', { name: 'Confirm banner changes' }))
  await waitFor(() => expect(request).toHaveBeenCalledTimes(2)); session('admin', true, 'owner-b'); view.rerender(detail()); await screen.findByRole('heading', { name: 'Current owner banner' }); await act(async () => finish([row]))
  expect(vi.mocked(request).mock.calls.some(([, options]) => options?.method === 'PATCH')).toBe(false); expect(sessionStorage.length).toBe(0)
})
