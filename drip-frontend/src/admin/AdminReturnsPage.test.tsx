import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/AuthProvider'
import { request } from '../api/client'
import { AdminReturnsPage } from './AdminReturnsPage'
import { returned, owner, other, rid } from '../../tests/fixtures/admin-returns'
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
vi.mock('../api/client', async original => ({ ...await original<typeof import('../api/client')>(), request: vi.fn() }))
function session(role = 'admin', verified = true, id = owner) { vi.mocked(useAuth).mockReturnValue({ user: { id, role, has_verified_email: verified, first_name: 'Test', last_name: null, email: 'admin@example.test' }, loading: false, error: null, signIn: vi.fn(), signOut: vi.fn(), acceptSession: vi.fn(), clearSession: vi.fn(), updateProfileNames: vi.fn() }) }
const page = () => <MemoryRouter initialEntries={[`/admin/returns/${rid}`]}><Routes><Route path="/admin/returns/:id" element={<AdminReturnsPage detail />} /></Routes></MemoryRouter>
beforeEach(() => { vi.mocked(request).mockReset(); sessionStorage.clear(); session() })
it.each([['customer', true], ['seller', true], ['Admin', true], ['admin', false]] as const)('blocks private reads for %s verified=%s', (role, verified) => { session(role, verified); render(page()); expect(request).not.toHaveBeenCalled() })
it('hides malformed private records', async () => { vi.mocked(request).mockResolvedValue({ customer: { email: 'Hidden private data' } }); render(page()); await screen.findByRole('alert'); expect(screen.queryByText('Hidden private data')).not.toBeInTheDocument() })
it('does not post after owner changes during preflight', async () => {
  let finish: (v: unknown) => void = () => {}, reads = 0
  vi.mocked(request).mockImplementation(() => ++reads === 2 ? new Promise(resolve => { finish = resolve }) : Promise.resolve(returned()))
  const view = render(page()); await screen.findByRole('button', { name: 'Review return action' }); fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Review return action' })); fireEvent.click(screen.getByRole('button', { name: 'Confirm return action' })); await waitFor(() => expect(reads).toBe(2)); session('admin', true, other); view.rerender(page()); await waitFor(() => expect(reads).toBe(3)); await act(async () => finish(returned())); expect(vi.mocked(request).mock.calls.some(([, o]) => o?.method === 'POST')).toBe(false)
})
