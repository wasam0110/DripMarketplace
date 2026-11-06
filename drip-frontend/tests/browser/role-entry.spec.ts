import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

async function setup(page: Page, role: string, initial: 'ready' | 'missing' | 'offline' = 'ready') {
  let active = initial === 'ready'
  const calls: { path: string; method: string; body: string | null }[] = []
  const user = { id: 'fixture-owner', role, email: 'owner@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: true }
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    calls.push({ path, method: route.request().method(), body: route.request().postData() })
    if (path.endsWith('/auth/refresh')) {
      if (initial === 'offline') return route.abort()
      return route.fulfill(active
        ? { json: { access_token: 'fixture-token' } }
        : { status: 401, json: { error: { message: 'No session' } } })
    }
    if (path.endsWith('/auth/login') || path.endsWith('/auth/verify-email')) {
      active = true
      return route.fulfill({ json: { access_token: 'fixture-token', user } })
    }
    if (path.endsWith('/auth/me')) return route.fulfill({ json: user })
    if (path.endsWith('/seller/me')) return route.fulfill({ json: {
      id: '11111111-1111-4111-8111-111111111111', brand_name: 'Fixture Label', status: 'pending_approval',
      registration_amount_due: '0.00', registration_paid_at: null,
    } })
    if (path.endsWith('/auth/logout')) {
      active = false
      return route.fulfill({ status: 204 })
    }
    if (path.endsWith('/cart')) return route.fulfill({ json: { items: [], item_count: 0, subtotal: '0', shipping_fee: '0', total: '0' } })
    return route.fulfill({ status: 404, json: { error: { message: 'Unexpected fixture request' } } })
  })
  return calls
}

for (const role of ['customer', 'seller', 'admin']) test(`${role} login follows the server role, not the URL`, async ({ page }) => {
  const calls = await setup(page, role, 'missing')
  await page.goto('/login?role=admin&next=https://other.example')
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeEnabled()
  await page.getByLabel('Email address', { exact: true }).fill('owner@example.test')
  await page.getByLabel('Password', { exact: true }).fill('Example123')
  if (role === 'admin') {
    await page.getByLabel('Administrator sign-in', { exact: true }).check()
    await page.getByLabel('Administrator authenticator code', { exact: true }).fill('123456')
  } else await expect(page.getByLabel('Administrator authenticator code', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL(new RegExp(`/${role === 'customer' ? 'account' : role}$`))
  const login = calls.filter(({ path }) => path.endsWith('/auth/login'))
  expect(login).toHaveLength(1)
  expect(JSON.parse(login[0].body!)).toEqual({ email: 'owner@example.test', password: 'Example123', ...(role === 'admin' ? { totp_code: '123456' } : {}) })
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain('fixture-token')
})

for (const role of ['seller', 'admin']) test(`${role} restored session has an accessible workspace and account navigation`, async ({ page }, info) => {
  const calls = await setup(page, role)
  await page.goto('/login')
  await expect(page).toHaveURL(new RegExp(`/${role}$`))
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(`${role === 'seller' ? 'Seller' : 'Admin'} workspace`)
  await expect(page.getByText(/No operational totals or actions/)).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath(`${role}-workspace.png`), fullPage: true })
  await page.getByRole('link', { name: 'Account settings and sign out' }).click()
  await page.getByRole('link', { name: `Open your ${role} workspace` }).click()
  await expect(page).toHaveURL(new RegExp(`/${role}$`))
  const privileged = calls.filter(({ path }) => /\/(sellers?|admin|payments)(\/|$)/.test(path))
  if (role === 'seller') {
    expect(privileged.length).toBeGreaterThan(0)
    expect(privileged.every(({ path, method }) => path === '/api/v1/seller/me' && method === 'GET')).toBe(true)
  } else expect(privileged).toEqual([])
})

for (const [role, workspace] of [['customer', 'seller'], ['customer', 'admin'], ['seller', 'admin'], ['admin', 'seller'], ['unknown', 'admin']]) test(`${role} cannot enter ${workspace}`, async ({ page }) => {
  await setup(page, role)
  await page.goto(`/${workspace}?role=${workspace}`)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('This workspace is not available to your account')
  await expect(page.getByText('owner@example.test', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Return to your workspace' })).toHaveAttribute('href', role === 'seller' ? '/seller' : role === 'admin' ? '/admin' : '/account')
})

for (const role of ['seller', 'admin']) test(`signed-out visitor cannot enter ${role}`, async ({ page }) => {
  await setup(page, role, 'missing')
  await page.goto(`/${role}`)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Sign in to your workspace')
  await expect(page.getByRole('link', { name: 'Sign in', exact: true })).toHaveAttribute('href', '/login')
})

test('session failure does not become a successful workspace entry', async ({ page }) => {
  await setup(page, 'seller', 'offline')
  await page.goto('/seller')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Session could not be restored')
  await expect(page.getByRole('alert')).toBeVisible()
})

for (const role of ['seller', 'admin']) test(`${role} callback and verification links use the restored role`, async ({ page }) => {
  const calls = await setup(page, role)
  await page.goto('/auth/callback')
  await expect(page.getByRole('link', { name: 'Continue to your account' })).toHaveAttribute('href', `/${role}`)
  await page.goto('/verify-email?token=fixture-verification')
  await page.getByRole('button', { name: 'Verify my email' }).click()
  await expect(page.getByRole('link', { name: 'Continue to your account' })).toHaveAttribute('href', `/${role}`)
  await expect(page).toHaveURL(/\/verify-email$/)
  expect(calls.filter(({ path }) => path.endsWith('/auth/verify-email'))).toHaveLength(1)
})

test('logout removes workspace access on a subsequent visit', async ({ page }) => {
  await setup(page, 'seller')
  await page.goto('/seller')
  await page.getByRole('link', { name: 'Account settings and sign out' }).click()
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Sign in', exact: true })).toBeVisible()
  await page.goto('/seller')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Sign in to your workspace')
})
