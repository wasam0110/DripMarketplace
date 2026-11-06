import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

for (const [status, title] of [
  ['pending_payment', 'Registration payment pending'], ['pending_approval', 'Application awaiting approval'],
  ['active', 'Brand approved'], ['suspended', 'Selling access suspended'], ['rejected', 'Application not approved'],
  ['unknown', 'Application status unavailable'],
]) test(`seller application: ${status}`, async ({ page }, info) => {
  let fail = false
  const requests: string[] = []
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: {
      id: 'seller-owner', role: 'seller', email: 'seller@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: true,
    } })
    if (path.endsWith('/cart')) return route.fulfill({ json: { items: [], item_count: 0, subtotal: '0', shipping_fee: '0', total: '0' } })
    requests.push(`${route.request().method()} ${path}`)
    if (path.endsWith('/seller/me')) return route.fulfill(fail
      ? { status: 503, json: { error: { message: 'Seller status temporarily unavailable' } } }
      : { json: { id: '11111111-1111-4111-8111-111111111111', brand_name: 'Fixture Label', status,
        registration_amount_due: status === 'pending_payment' ? '5000.00' : '0.00', registration_paid_at: null } })
    return route.fulfill({ status: 404, json: { error: { message: 'Unexpected request' } } })
  })
  await page.goto('/seller')
  await expect(page.getByText(title, { exact: true })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  if (status === 'pending_payment') await page.screenshot({ path: info.outputPath('seller-payment-pending.png'), fullPage: true })
  fail = true
  await page.getByRole('button', { name: 'Refresh seller status' }).click()
  await expect(page.getByRole('alert')).toContainText('Seller status temporarily unavailable')
  await expect(page.getByText('Fixture Label', { exact: true })).toHaveCount(0)
  fail = false
  await page.getByRole('button', { name: 'Refresh seller status' }).click()
  await expect(page.getByText(title, { exact: true })).toBeVisible()
  expect(requests.length).toBeGreaterThanOrEqual(3)
  expect(requests.every((request) => request === 'GET /api/v1/seller/me')).toBe(true)
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain('Fixture Label')
})
