import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { ApiError, request } from '../api/client'
import { SellerStatus, validateSellerSummary } from './SellerStatus'

vi.mock('../api/client', async (original) => ({ ...await original<typeof import('../api/client')>(), request: vi.fn() }))
const profile = { id: '11111111-1111-4111-8111-111111111111', brand_name: 'Test Label', status: 'pending_approval', registration_amount_due: '0.00', registration_paid_at: null }
const page = (verified = true, owner = 'owner') => <MemoryRouter><SellerStatus key={owner} verified={verified} /></MemoryRouter>
beforeEach(() => { vi.mocked(request).mockReset(); vi.mocked(request).mockResolvedValue(profile) })

it.each([
  ['pending_payment', 'Registration payment pending'], ['pending_approval', 'Application awaiting approval'],
  ['active', 'Brand approved'], ['suspended', 'Selling access suspended'], ['rejected', 'Application not approved'],
  ['future_state', 'Application status unavailable'], ['constructor', 'Application status unavailable'],
])('renders server state %s without inventing actions', async (status, title) => {
  vi.mocked(request).mockResolvedValue({ ...profile, status })
  render(page())
  expect(await screen.findByText(title)).toBeInTheDocument()
  expect(screen.getAllByRole('button')).toHaveLength(1)
  expect(request).toHaveBeenCalledWith('/seller/me', expect.objectContaining({ authenticated: true, cache: 'no-store' }))
})

it('does not fetch an unverified seller profile', () => {
  render(page(false))
  expect(screen.getByText('Verify your email first')).toBeInTheDocument()
  expect(request).not.toHaveBeenCalled()
})

it('distinguishes zero fees from a paid receipt', async () => {
  render(page())
  expect(await screen.findByText('No payment due; no paid receipt recorded.')).toBeInTheDocument()
  expect(screen.queryByText(/Recorded on/)).not.toBeInTheDocument()
})

it('shows a recorded receipt without claiming approval', async () => {
  vi.mocked(request).mockResolvedValue({ ...profile, registration_paid_at: '2026-10-27T00:00:00Z' })
  render(page())
  expect(await screen.findByText(/Recorded on/)).toBeInTheDocument()
  expect(screen.getByText('Application awaiting approval')).toBeInTheDocument()
  expect(screen.queryByText('Brand approved')).not.toBeInTheDocument()
})

it.each([403, 404, 500])('does not convert HTTP %s into approval or rejection', async (status) => {
  vi.mocked(request).mockRejectedValue(new ApiError('Read unavailable', status))
  render(page())
  expect(await screen.findByRole('alert')).toHaveTextContent('Read unavailable')
  expect(screen.queryByText('Test Label')).not.toBeInTheDocument()
  expect(screen.queryByText('Application not approved')).not.toBeInTheDocument()
})

it('clears prior status when a refresh fails', async () => {
  render(page())
  await screen.findByText('Application awaiting approval')
  vi.mocked(request).mockRejectedValue(new Error('Network unavailable'))
  fireEvent.click(screen.getByRole('button', { name: 'Refresh seller status' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Network unavailable')
  expect(screen.queryByText('Test Label')).not.toBeInTheDocument()
})

it('discards a delayed response after the owner changes', async () => {
  let resolve!: (value: typeof profile) => void
  vi.mocked(request).mockReturnValueOnce(new Promise((done) => { resolve = done }))
  const view = render(page())
  await waitFor(() => expect(request).toHaveBeenCalledTimes(1))
  const options = vi.mocked(request).mock.calls[0][1]!
  vi.mocked(request).mockResolvedValue({ ...profile, brand_name: 'New Label' })
  view.rerender(page(true, 'new-owner'))
  expect(await screen.findByText('New Label')).toBeInTheDocument()
  await act(async () => resolve(profile))
  expect(options.signal?.aborted).toBe(true)
  expect(screen.queryByText('Test Label')).not.toBeInTheDocument()
})

it.each([
  null, { ...profile, id: 'bad' }, { ...profile, status: null }, { ...profile, brand_name: '' },
  { ...profile, registration_amount_due: -1 }, { ...profile, registration_amount_due: 'NaN' },
  { ...profile, registration_amount_due: '-1' }, { ...profile, registration_amount_due: '1.001' },
  { ...profile, registration_paid_at: 'not a date' },
  { ...profile, registration_paid_at: '2026-10-27T00:00:00Z', registration_amount_due: '5.00' },
])('rejects malformed or contradictory profile data %#', (value) => {
  expect(() => validateSellerSummary(value as typeof profile)).toThrow()
})
