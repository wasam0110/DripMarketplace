import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

async function setup(page: Page, role = 'seller', verified = true, mode = 'ready') {
  const calls: string[] = []
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (url.pathname.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, email: 'seller@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (url.pathname.endsWith('/seller/products')) {
      calls.push(`${route.request().method()} ${url.search}`)
      expect(route.request().headers().authorization).toBe('Bearer fixture-token')
      if (mode === 'denied') return route.fulfill({ status: 403, json: { error: { message: 'Seller is not active' } } })
      const count = mode === 'empty' || url.searchParams.get('page') === '2' ? 0 : url.searchParams.get('status') === 'draft' ? 1 : 20
      return route.fulfill({ json: { data: Array.from({ length: count }, (_, i) => ({ id: `11111111-1111-4111-8111-${String(i).padStart(12, '0')}`, name: `Linen shirt ${i + 1}`, category: 'Clothing', price: '2500.00', total_stock: 8, image_count: 2, is_published: false })), slot_info: { total_slots: 30, slots_used: 20, slots_available: 10 } } })
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return calls
}
test('catalogue filters, paginates and refreshes without writes', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto('/seller/products')
  await expect(page.getByRole('heading', { name: 'Linen shirt 1', exact: true })).toBeVisible()
  // Development StrictMode can start and abort an initial read twice.
  expect(calls.length).toBeGreaterThan(0)
  expect(calls.every((call) => call === 'GET ?status=all&page=1')).toBe(true)
  calls.length = 0
  await page.getByRole('button', { name: 'Next page' }).click()
  await expect(page.getByRole('heading', { name: 'No products on this page' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Next page' })).toBeDisabled()
  await page.getByLabel('Product status').selectOption('draft')
  await expect(page.getByRole('heading', { name: 'Linen shirt 1', exact: true })).toBeVisible()
  await expect(page.getByText('Page 1', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Refresh catalogue' }).click()
  await expect(page.getByRole('heading', { name: 'Linen shirt 1', exact: true })).toBeVisible()
  expect(calls).toEqual(['GET ?status=all&page=2', 'GET ?status=draft&page=1', 'GET ?status=draft&page=1'])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('seller-catalogue.png'), fullPage: true })
})
test('denied reads are not presented as empty catalogues', async ({ page }) => {
  await setup(page, 'seller', true, 'denied'); await page.goto('/seller/products')
  await expect(page.getByRole('alert')).toContainText('Seller is not active')
  await expect(page.getByRole('heading', { name: 'No products on this page' })).toHaveCount(0)
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to view your catalogue'], ['customer', true, 'A seller account is required'], ['admin', true, 'A seller account is required'], ['seller', false, 'Verify your email first']] as const) {
  test(`${role} verified=${verified} cannot read seller catalogue`, async ({ page }) => {
    const calls = await setup(page, role, verified); await page.goto('/seller/products')
    await expect(page.getByRole('heading', { name: heading })).toBeVisible(); expect(calls).toEqual([])
  })
}
