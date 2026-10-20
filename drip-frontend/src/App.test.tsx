import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import App from './App'
import { setAccessToken } from './api/client'

const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })

beforeEach(() => {
  setAccessToken(null)
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.includes('/auth/refresh')) return response({ error: { message: 'No session' } }, 401)
    if (url.includes('/brands')) return response({ data: [], pagination: { page: 1, per_page: 24, total: 0 } })
    return response({ data: [], pagination: { next_cursor: null, has_next: false, limit: 20 } })
  }))
})

function renderAt(route = '/') { return render(<MemoryRouter initialEntries={[route]}><App /></MemoryRouter>) }

it('renders the approved homepage and real empty catalogue state', async () => {
  renderAt()
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Good labels.Great finds.')
  expect(await screen.findByText('Room for something good.')).toBeInTheDocument()
  expect(screen.queryByText('PKR 8,900')).not.toBeInTheDocument()
})

it('opens and closes mobile navigation with keyboard dismissal', async () => {
  renderAt()
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Open menu' }))
  const navigation = screen.getByRole('navigation', { name: 'Mobile navigation' })
  expect(navigation).toBeInTheDocument()
  const link = navigation.querySelector('a')!
  link.focus()
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('navigation', { name: 'Mobile navigation' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Open menu' })).toHaveFocus()
})

it('submits search through the URL and backend query', async () => {
  renderAt()
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Search clothing' }))
  await user.type(screen.getByRole('searchbox', { name: 'Search clothing' }), 'linen')
  await user.click(screen.getByRole('button', { name: 'Search' }))
  expect(await screen.findByRole('heading', { name: 'Your edit: “linen”' })).toBeInTheDocument()
  await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('q=linen'), expect.anything()))
})

it('keeps the authenticator field admin-only', async () => {
  renderAt('/login')
  expect(screen.queryByLabelText('Administrator authenticator code')).not.toBeInTheDocument()
  await userEvent.click(screen.getByLabelText('Administrator sign-in'))
  expect(screen.getByLabelText('Administrator authenticator code')).toBeRequired()
})

it('signs in using the backend contract and displays the returned profile', async () => {
  const user = userEvent.setup()
  vi.mocked(fetch).mockImplementation(async (input) => {
    if (String(input).endsWith('/auth/login')) return response({
      access_token: 'in-memory', user: { id: '1', email: 'customer@example.com', role: 'customer', first_name: 'Ayesha', has_verified_email: true },
    })
    return response({ error: { message: 'No session' } }, 401)
  })
  renderAt('/login')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled())
  await user.type(screen.getByLabelText('Email address'), 'customer@example.com')
  await user.type(screen.getByLabelText('Password'), 'Example123')
  await user.click(screen.getByRole('button', { name: 'Sign in' }))
  expect(await screen.findByRole('heading', { name: 'Welcome, Ayesha.' })).toBeInTheDocument()
  expect(localStorage.length).toBe(0)
})

it('shows recoverable errors and retries failed catalogue requests', async () => {
  let attempts = 0
  vi.mocked(fetch).mockImplementation(async (input) => {
    if (String(input).includes('/auth/')) return response({ error: { message: 'No session' } }, 401)
    if (++attempts === 1) return response({ error: { message: 'Catalogue unavailable' } }, 503)
    return response({ data: [], pagination: { has_next: false } })
  })
  renderAt()
  expect(await screen.findByRole('alert')).toHaveTextContent('Catalogue unavailable')
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('Room for something good.')).toBeInTheDocument()
})

it('protects the account screen without a session', async () => {
  renderAt('/account')
  expect(await screen.findByText('Let’s get you back in.')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Sign out' })).not.toBeInTheDocument()
})

it('renders a useful not-found route', async () => {
  renderAt('/does-not-exist')
  expect(await screen.findByText('This piece of the story is missing.')).toBeInTheDocument()
})

it('submits registration fields and shows verification instructions, not a fake login', async () => {
  const user = userEvent.setup()
  vi.mocked(fetch).mockImplementation(async (input) =>
    String(input).includes('/auth/register')
      ? response({ message: 'Check your inbox' }, 201)
      : response({ error: { message: 'No session' } }, 401))
  renderAt('/register')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Create account' })).toBeEnabled())
  await user.type(screen.getByLabelText('First name'), 'Ayesha')
  await user.type(screen.getByLabelText('Last name'), 'Khan')
  await user.type(screen.getByLabelText('Email address'), 'ayesha@example.com')
  await user.type(screen.getByLabelText('Password'), 'Example123')
  await user.click(screen.getByRole('button', { name: 'Create account' }))
  expect(await screen.findByText(/Your inbox has the next step/)).toBeInTheDocument()
  const options = vi.mocked(fetch).mock.calls.find(([url]) => String(url).endsWith('/auth/register'))![1]!
  expect(JSON.parse(String(options.body))).toEqual({
    first_name: 'Ayesha', last_name: 'Khan', email: 'ayesha@example.com', password: 'Example123',
  })
})

it('keeps password-reset requests enumeration safe', async () => {
  vi.mocked(fetch).mockImplementation(async (input) =>
    String(input).includes('/auth/forgot-password')
      ? response({ message: 'Email queued if account exists' })
      : response({ error: { message: 'No session' } }, 401))
  renderAt('/forgot-password')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send reset instructions' })).toBeEnabled())
  await userEvent.type(screen.getByLabelText('Email address'), 'unknown@example.com')
  await userEvent.click(screen.getByRole('button', { name: 'Send reset instructions' }))
  expect(await screen.findByText(/If an account exists for that email/)).toBeInTheDocument()
})

it('requires matching new passwords before sending the reset', async () => {
  renderAt('/reset-password?token=example-token')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Reset password' })).toBeEnabled())
  await userEvent.type(screen.getByLabelText('New password'), 'Example123')
  await userEvent.type(screen.getByLabelText('Confirm password'), 'Different123')
  await userEvent.click(screen.getByRole('button', { name: 'Reset password' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('The passwords don’t match.')
  expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes('/auth/reset-password'))).toBe(false)
})

it('consumes an email-verification token only after an explicit action', async () => {
  vi.mocked(fetch).mockImplementation(async (input) =>
    String(input).includes('/auth/verify-email')
      ? response({ access_token: 'verified-token', user: { id: '1', email: 'ayesha@example.com', role: 'customer', first_name: 'Ayesha', has_verified_email: true } })
      : response({ error: { message: 'No session' } }, 401))
  renderAt('/verify-email?token=one-use')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Verify my email' })).toBeEnabled())
  expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes('/auth/verify-email'))).toBe(false)
  await userEvent.click(screen.getByRole('button', { name: 'Verify my email' }))
  expect(await screen.findByText('You’re all set.')).toBeInTheDocument()
  expect(vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes('/auth/verify-email'))).toHaveLength(1)
})

it('does not report successful logout when the server fails', async () => {
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input)
    if (url.endsWith('/auth/refresh')) return response({ access_token: 'session' })
    if (url.endsWith('/auth/me')) return response({ id: '1', first_name: 'Ayesha', email: 'a@example.com', role: 'customer', has_verified_email: true })
    return response({ error: { message: 'Sign-out unavailable; try again' } }, 503)
  })
  renderAt('/account')
  await userEvent.click(await screen.findByRole('button', { name: 'Sign out' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Sign-out unavailable')
  expect(screen.getByRole('heading', { name: 'Welcome, Ayesha.' })).toBeInTheDocument()
})
