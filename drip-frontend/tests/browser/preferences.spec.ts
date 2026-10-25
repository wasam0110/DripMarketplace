import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const initial = { email_order_updates: true, email_promotions: false, email_new_arrivals: false, sms_order_updates: false, whatsapp_order_updates: true }
async function setup(page: Page, mode: 'normal' | 'guest' | 'lost' | 'denied' | 'mismatch' | 'invalid' | 'failed' = 'normal') {
  const calls = { reads: 0, writes: [] as unknown[] }
  let settings = { ...initial }
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(mode === 'guest' ? { status: 401, json: { error: { message: 'Guest' } } } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'buyer', first_name: 'Sara', email: 'sara@example.test', role: 'customer' } })
    if (path.endsWith('/auth/logout')) return route.fulfill({ status: 204 })
    if (path.endsWith('/me/notification-preferences')) {
      expect(req.headers().authorization).toBe('Bearer fixture-token')
      if (req.method() === 'PATCH') {
        calls.writes.push(req.postDataJSON())
        if (mode === 'denied') return route.fulfill({ status: 403, json: { error: { message: 'Preference update denied.' } } })
        if (mode !== 'mismatch') settings = { ...settings, ...req.postDataJSON() }
        if (mode === 'lost') return route.abort('failed')
      } else calls.reads++
      if (mode === 'failed') return route.fulfill({ status: 503, json: { error: { message: 'Preferences unavailable.' } } })
      return route.fulfill({ json: mode === 'invalid' ? { ...settings, sms_order_updates: 'false' } : settings })
    }
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  return calls
}

test('saved choices load without autosave and only changed preferences are submitted', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto('/account')
  await page.getByRole('link', { name: 'Notification preferences', exact: true }).click()
  await expect(page.getByRole('checkbox', { name: 'Order updates by email', exact: true })).toBeChecked()
  await expect(page.getByRole('checkbox', { name: 'Promotions by email', exact: true })).not.toBeChecked()
  await expect(page.getByRole('button', { name: 'Save notification preferences', exact: true })).toBeDisabled()
  await page.getByRole('checkbox', { name: 'Order updates by email', exact: true }).uncheck()
  await page.getByRole('checkbox', { name: 'New arrivals by email', exact: true }).check()
  expect(calls.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('notification-preferences.png'), fullPage: true })
  await page.getByRole('button', { name: 'Save notification preferences', exact: true }).click()
  await expect(page.getByText('Notification preferences saved.', { exact: true })).toBeVisible()
  expect(calls.writes).toEqual([{ email_order_updates: false, email_new_arrivals: true }])
  await page.reload()
  await expect(page.getByRole('checkbox', { name: 'Order updates by email', exact: true })).not.toBeChecked()
  await expect(page.getByRole('checkbox', { name: 'New arrivals by email', exact: true })).toBeChecked()
})

test('discard and refresh reset drafts without writing or persisting choices', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/account/notifications')
  const option = page.getByRole('checkbox', { name: 'Promotions by email', exact: true })
  await option.check()
  await page.getByRole('button', { name: 'Discard preference changes' }).click()
  await expect(option).not.toBeChecked()
  await option.check()
  await page.getByRole('button', { name: 'Refresh notification preferences' }).click()
  await expect(option).not.toBeChecked()
  expect(calls.writes).toEqual([])
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))).not.toMatch(/email_promotions|notification.preferences/)
})

test('lost responses lock further changes even after refreshing server state', async ({ page }) => {
  const calls = await setup(page, 'lost')
  await page.goto('/account/notifications')
  await page.getByRole('checkbox', { name: 'Promotions by email', exact: true }).check()
  await page.getByRole('button', { name: 'Save notification preferences', exact: true }).click()
  await expect(page.getByText('Further changes are locked', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Refresh notification preferences' }).click()
  await expect(page.getByRole('checkbox', { name: 'Promotions by email', exact: true })).toBeChecked()
  await expect(page.getByRole('checkbox', { name: 'Promotions by email', exact: true })).toBeDisabled()
  expect(calls.writes).toHaveLength(1)
})

test('definite rejection keeps the draft and does not claim success', async ({ page }) => {
  const calls = await setup(page, 'denied')
  await page.goto('/account/notifications')
  await page.getByRole('checkbox', { name: 'Promotions by email', exact: true }).check()
  await page.getByRole('button', { name: 'Save notification preferences', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Preference update denied.')
  await expect(page.getByRole('checkbox', { name: 'Promotions by email', exact: true })).toBeChecked()
  await expect(page.getByRole('button', { name: 'Save notification preferences', exact: true })).toBeEnabled()
  await expect(page.getByText('Notification preferences saved.', { exact: true })).not.toBeVisible()
  expect(calls.writes).toHaveLength(1)
})

test('a mismatched success response is treated as unconfirmed', async ({ page }) => {
  await setup(page, 'mismatch')
  await page.goto('/account/notifications')
  await page.getByRole('checkbox', { name: 'Promotions by email', exact: true }).check()
  await page.getByRole('button', { name: 'Save notification preferences', exact: true }).click()
  await expect(page.getByText('Further changes are locked', { exact: false })).toBeVisible()
  await expect(page.getByText('Notification preferences saved.', { exact: true })).not.toBeVisible()
})

for (const mode of ['invalid', 'failed'] as const) test(`${mode} reads do not invent preference defaults`, async ({ page }) => {
  const calls = await setup(page, mode)
  await page.goto('/account/notifications')
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByRole('checkbox')).toHaveCount(0)
  expect(calls.writes).toEqual([])
})

test('guests never request private preferences', async ({ page }) => {
  const calls = await setup(page, 'guest')
  await page.goto('/account/notifications')
  await expect(page.getByText('Sign in to manage your account.')).toBeVisible()
  expect(calls.reads).toBe(0)
})

test('sign-out discards notification drafts before back navigation', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/account/notifications')
  await page.getByRole('checkbox', { name: 'Promotions by email', exact: true }).check()
  await page.getByRole('link', { name: 'Back to account' }).click()
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Sign out', exact: true })).not.toBeVisible()
  const reads = calls.reads
  await page.goBack()
  await expect(page.getByText('Sign in to manage your account.')).toBeVisible()
  await expect(page.getByRole('checkbox')).toHaveCount(0)
  expect(calls.reads).toBe(reads)
  expect(calls.writes).toEqual([])
})
