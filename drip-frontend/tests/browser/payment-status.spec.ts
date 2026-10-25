import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111'
async function setup(page: Page, mode = 'pending', guest = false) {
  const calls: { method: string; token?: string }[] = []
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(guest ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role: 'customer', email: 'buyer@example.test' } })
    if (path.includes('/payments/')) {
      calls.push({ method: req.method(), token: req.headers()['x-guest-token'] })
      expect(path).toBe(`/api/v1/payments/${id}/status`)
      if (!guest) expect(req.headers().authorization).toBe('Bearer fixture-token')
      if (mode === 'denied') return route.fulfill({ status: 403, json: { error: { message: 'Denied' } } })
      return route.fulfill({ json: { order_id: mode === 'foreign' ? 'other' : id, payment_id: id, status: mode, method: 'payfast', amount: '1250.00', gateway_reference: null, paid_at: null } })
    }
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  return calls
}
test('success return still shows pending backend status', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto(`/order/success/${id}?status=paid&token=untrusted#paid`)
  await expect(page.getByRole('heading', { name: 'Payment pending' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Payment recorded' })).toHaveCount(0)
  await expect(page).toHaveURL(new RegExp(`/order/success/${id}$`))
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('payment-status.png'), fullPage: true })
  const beforeRefresh = calls.length // Development Strict Mode can abort/restart initial reads.
  await page.getByRole('button', { name: 'Refresh payment status' }).click()
  await expect(page.getByRole('heading', { name: 'Payment pending' })).toBeVisible()
  expect(calls).toHaveLength(beforeRefresh + 1)
  expect(calls.every((call) => call.method === 'GET')).toBe(true)
})
test('failure return can show completed backend status', async ({ page }) => {
  await setup(page, 'completed')
  await page.goto(`/payments/${id}?payment=failed`)
  await expect(page.getByRole('heading', { name: 'Payment recorded' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Payment failed' })).toHaveCount(0)
})
test('guest must explicitly provide a private header code', async ({ page }) => {
  const calls = await setup(page, 'pending', true)
  await page.goto(`/order/success/${id}`)
  await expect(page.getByLabel('Private guest access code')).toBeVisible()
  expect(calls).toHaveLength(0)
  await page.getByLabel('Private guest access code').fill('private-fixture-code')
  await page.getByRole('button', { name: 'Check guest payment' }).click()
  await expect(page.getByRole('heading', { name: 'Payment pending' })).toBeVisible()
  expect(calls.length).toBeGreaterThan(0)
  expect(calls.every((call) => call.method === 'GET' && call.token === 'private-fixture-code')).toBe(true)
  expect(page.url()).not.toContain('private-fixture-code')
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain('private-fixture-code')
  await page.getByRole('button', { name: 'Clear guest access' }).click()
  await expect(page.getByLabel('Private guest access code')).toHaveValue('')
  await expect(page.getByRole('heading', { name: 'Payment pending' })).toHaveCount(0)
})
for (const mode of ['denied', 'foreign']) test(`${mode} status never exposes a payment panel`, async ({ page }) => {
  await setup(page, mode)
  await page.goto(`/payments/${id}`)
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByText('Payment amount (PKR)', { exact: true })).toHaveCount(0)
})
for (const [mode, label] of [['processing', 'Payment processing'], ['failed', 'Payment failed'], ['refunded', 'Payment refunded'], ['future', 'Payment status unavailable']]) test(`${mode} is displayed without a payment action`, async ({ page }) => {
  const calls = await setup(page, mode)
  await page.goto(`/payments/${id}`)
  await expect(page.getByRole('heading', { name: label, exact: true })).toBeVisible()
  expect(calls.every((call) => call.method === 'GET')).toBe(true)
  await expect(page.getByRole('button', { name: /pay now|retry payment/i })).toHaveCount(0)
})
test('invalid order references never request payment data', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/payments/invalid')
  await expect(page.getByRole('heading', { name: 'Payment reference unavailable' })).toBeVisible()
  expect(calls).toHaveLength(0)
})
