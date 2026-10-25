import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

async function setup(page: Page, session = 'ready') {
  const calls: string[] = []
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    calls.push(path)
    if (path.endsWith('/auth/refresh')) {
      if (session === 'offline') return route.abort()
      if (session === 'missing') return route.fulfill({ status: 401, json: { error: { message: 'No session' } } })
      return route.fulfill({ json: { access_token: 'fixture-token' } })
    }
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role: 'customer', email: 'buyer@example.test' } })
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  return calls
}
test('callback restores the cookie-backed session and links to account', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/auth/callback')
  await expect(page.getByRole('heading', { name: 'You’re signed in' })).toBeVisible()
  await page.getByRole('link', { name: 'Continue to your account' }).click()
  await expect(page.getByRole('heading', { name: 'Your account', exact: true })).toBeVisible()
  expect(calls.filter((path) => path.endsWith('/auth/refresh'))).toHaveLength(1)
  expect(calls.some((path) => path.includes('/google'))).toBe(false)
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain('fixture-token')
})
for (const outcome of ['cancelled', 'failed', 'untrusted-provider-detail']) test(`${outcome} shows a safe message even with an existing session`, async ({ page }, info) => {
  await setup(page)
  await page.goto(`/auth/callback?error=${outcome}&code=private-code#access_token=private-token`)
  await expect(page.getByRole('heading', { name: outcome === 'cancelled' ? 'Sign-in cancelled' : 'Sign-in could not be completed' })).toBeVisible()
  await expect(page).toHaveURL(/\/auth\/callback$/)
  await expect(page.getByText('untrusted-provider-detail', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'You’re signed in' })).toHaveCount(0)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  if (outcome === 'cancelled') await page.screenshot({ path: info.outputPath('google-callback.png'), fullPage: true })
})
for (const session of ['missing', 'offline']) test(`${session} session never claims sign-in or retries Google`, async ({ page }) => {
  const calls = await setup(page, session)
  await page.goto('/auth/callback')
  await expect(page.getByRole('heading', { name: 'Session could not be restored' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Return to sign in' })).toBeVisible()
  expect(calls.filter((path) => path.endsWith('/auth/refresh'))).toHaveLength(1)
  expect(calls.some((path) => path.includes('/google'))).toBe(false)
})
test('Google remains gated without configured feature flag', async ({ page }) => {
  await setup(page, 'missing')
  await page.goto('/login')
  await expect(page.getByRole('button', { name: 'Continue with Google' })).toBeDisabled()
})
