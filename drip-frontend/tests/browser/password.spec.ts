import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const credentials = { current_password: ' OldFixture1 ', new_password: ' NewFixture2 ', confirm_password: ' NewFixture2 ' }
async function setup(page: Page, mode: 'success' | 'wrong' | 'oauth' | 'expired' | 'lost' | 'unexpected' | 'guest' = 'success') {
  const calls = { writes: [] as unknown[], logouts: 0 }
  let revoked = false
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(mode === 'guest' || revoked ? { status: 401, json: { error: { message: 'Not signed in' } } } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'buyer', email: 'buyer@example.test', first_name: 'Buyer', role: 'customer' } })
    if (path.endsWith('/auth/logout')) { calls.logouts++; return route.fulfill({ status: 204 }) }
    if (path.endsWith('/me/change-password')) {
      expect(req.method()).toBe('POST')
      expect(req.headers().authorization).toBe('Bearer fixture-token')
      calls.writes.push(req.postDataJSON())
      if (mode === 'wrong' || mode === 'oauth' || mode === 'expired') return route.fulfill({ status: mode === 'expired' ? 401 : 422, json: { error: { message: mode === 'wrong' ? 'Current password is incorrect.' : mode === 'oauth' ? 'Cannot change password for OAuth-linked accounts.' : 'Session expired. Sign in again.' } } })
      if (mode === 'lost') return route.abort('failed')
      if (mode === 'unexpected') return route.fulfill({ json: { changed: true } })
      revoked = true
      return route.fulfill({ status: 204 })
    }
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  return calls
}
async function fill(page: Page) {
  await page.getByLabel('Current password', { exact: true }).fill(credentials.current_password)
  await page.getByLabel('New password', { exact: true }).fill(credentials.new_password)
  await page.getByLabel('Confirm new password', { exact: true }).fill(credentials.confirm_password)
}
test('confirmed password change clears local authentication without a redundant logout', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto('/account')
  await page.getByRole('link', { name: 'Change your password', exact: true }).click()
  await fill(page)
  await expect(page.getByLabel('Current password', { exact: true })).toHaveAttribute('type', 'password')
  expect(calls.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('change-password.png'), fullPage: true })
  await page.getByRole('button', { name: 'Change password and sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Password changed', exact: true })).toBeVisible()
  expect(calls.writes).toEqual([credentials])
  expect(calls.logouts).toBe(0)
  await page.getByRole('link', { name: 'Sign in again', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible()
  await expect(page.getByLabel('Password', { exact: true })).toHaveValue('')
  expect(page.url()).not.toMatch(/Fixture/)
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))).not.toMatch(/Fixture|current_password|new_password|confirm_password/)
})
test('validation and clear controls never send a password change', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/account/password')
  await fill(page)
  await page.getByLabel('New password', { exact: true }).fill('weak')
  await page.getByRole('button', { name: 'Change password and sign out' }).click()
  await expect(page.getByRole('alert')).toContainText('8–128')
  await page.getByLabel('New password', { exact: true }).fill(credentials.new_password)
  await page.getByLabel('Confirm new password', { exact: true }).fill('Different2')
  await page.getByRole('button', { name: 'Change password and sign out' }).click()
  await expect(page.getByRole('alert')).toContainText('do not match')
  await page.getByRole('button', { name: 'Clear password fields', exact: true }).click()
  await expect(page.getByLabel('Current password', { exact: true })).toHaveValue('')
  await expect(page.getByLabel('New password', { exact: true })).toHaveValue('')
  await expect(page.getByLabel('Confirm new password', { exact: true })).toHaveValue('')
  expect(calls.writes).toEqual([])
})
for (const mode of ['wrong', 'oauth', 'expired'] as const) test(`${mode} rejection clears credentials without claiming success or replaying`, async ({ page }) => {
  const calls = await setup(page, mode)
  await page.goto('/account/password')
  await fill(page)
  await page.getByRole('button', { name: 'Change password and sign out' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByLabel('Current password', { exact: true })).toHaveValue('')
  await expect(page.getByLabel('New password', { exact: true })).toHaveValue('')
  await expect(page.getByLabel('Confirm new password', { exact: true })).toHaveValue('')
  await expect(page.getByRole('button', { name: 'Change password and sign out' })).toBeEnabled()
  await expect(page.getByRole('heading', { name: 'Password changed', exact: true })).not.toBeVisible()
  expect(calls.writes).toHaveLength(1)
})
for (const mode of ['lost', 'unexpected'] as const) test(`${mode} response locks replay and offers local sign-in recovery`, async ({ page }) => {
  const calls = await setup(page, mode)
  await page.goto('/account/password')
  await fill(page)
  await page.getByRole('button', { name: 'Change password and sign out' }).click()
  await expect(page.getByText('The change may have reached the server.', { exact: false })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Change password and sign out' })).toBeDisabled()
  await expect(page.getByLabel('Current password', { exact: true })).toHaveValue('')
  await expect(page.getByLabel('New password', { exact: true })).toHaveValue('')
  await page.getByRole('button', { name: 'Clear local session and go to sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible()
  expect(calls.writes).toHaveLength(1)
  expect(calls.logouts).toBe(0)
})
test('guests cannot submit password changes', async ({ page }) => {
  const calls = await setup(page, 'guest')
  await page.goto('/account/password')
  await expect(page.getByText('Sign in to manage your account.')).toBeVisible()
  await expect(page.getByLabel('Current password', { exact: true })).not.toBeVisible()
  expect(calls.writes).toEqual([])
})
