import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/AuthProvider'
import { request } from '../api/client'
import { AdminProductsPage } from './AdminProductsPage'
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
vi.mock('../api/client', async (original) => ({ ...await original<typeof import('../api/client')>(), request: vi.fn() }))
function session(role = 'admin', verified = true, id = 'owner-a', loading = false) {
  vi.mocked(useAuth).mockReturnValue({ user: { id, role, has_verified_email: verified, first_name: 'Test', last_name: null, email: 'admin@example.test' }, loading, error: null, signIn: vi.fn(), signOut: vi.fn(), acceptSession: vi.fn(), clearSession: vi.fn(), updateProfileNames: vi.fn() })
}
const page = (url = '/admin/products') => <MemoryRouter initialEntries={[url]}><AdminProductsPage /></MemoryRouter>
beforeEach(() => { vi.mocked(request).mockReset(); session(); sessionStorage.clear() })
it.each([['seller', true], ['customer', true], ['Admin', true], ['admin', false]] as const)('blocks product reads for %s verified=%s', (role, verified) => {
  session(role, verified); render(page()); expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(role === 'admin' ? 'Verify your email' : 'administrator account'); expect(request).not.toHaveBeenCalled()
})
it('does not read before session restoration or with invalid URL filters', () => {
  session('admin', true, 'owner-a', true); const view = render(page()); expect(request).not.toHaveBeenCalled(); view.unmount()
  session(); render(page('/admin/products?seller_id=invalid')); expect(screen.getByRole('alert')).toHaveTextContent('valid seller reference'); expect(request).not.toHaveBeenCalled()
})
it('aborts and discards old private results when the admin owner changes', async () => {
  let finish: (value: unknown) => void = () => {}
  vi.mocked(request).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve })).mockResolvedValue({ data: [], pagination: { page: 1, per_page: 25, total: 0 } })
  const view = render(page()); await waitFor(() => expect(request).toHaveBeenCalledTimes(1))
  session('admin', true, 'owner-b'); view.rerender(page()); await screen.findByText('No products on this page')
  expect(vi.mocked(request).mock.calls[0][1]?.signal?.aborted).toBe(true)
  await act(async () => finish({ data: [{ id: '11111111-1111-4111-8111-111111111111', seller_id: '22222222-2222-4222-8222-222222222222', name: 'Old private draft', slug: 'draft', price: '1500.25', is_published: false, admin_hidden: true }], pagination: { page: 1, per_page: 25, total: 1 } }))
  expect(screen.queryByText('Old private draft')).not.toBeInTheDocument()
})
