import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const seller = '11111111-1111-4111-8111-111111111111', product = '22222222-2222-4222-8222-222222222222', variant = '33333333-3333-4333-8333-333333333333'
async function setup(page: Page, mode = 'ready', role = 'seller', verified = true) {
  let stock = 10, threshold = 5
  const writes: { method: string; body: Record<string, unknown> }[] = [], reads: string[] = []
  const row = () => ({ variant_id: variant, product_id: product, product_name: 'Linen shirt', sku: 'WHZ-TEST', size: 'M', colour: 'Blue', stock, reserved: 3, available: stock - 3, reorder_point: threshold, is_low_stock: stock - 3 <= threshold, last_restocked_at: null })
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, email: 'seller@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.includes('/seller/')) reads.push(`${method} ${path}${url.search}`)
    if (path.endsWith('/seller/me')) return route.fulfill({ json: { id: seller, brand_name: 'Fixture Label', status: mode === 'inactive' ? 'suspended' : 'active', registration_amount_due: '0.00', registration_paid_at: null } })
    if (path.includes('/seller/inventory')) {
      if (method !== 'GET') {
        const body = route.request().postDataJSON(); writes.push({ method, body })
        expect(route.request().headers().authorization).toBe('Bearer fixture-token')
        if (mode === 'rejected') return route.fulfill({ status: 422, json: { error: { message: 'Stock cannot fall below reserved units' } } })
        if (mode === 'lost') return route.abort()
        if (method === 'PUT') {
          stock = body.stock; threshold = body.reorder_point ?? threshold
          return route.fulfill({ json: mode === 'mismatch' ? { ...row(), variant_id: product } : row() })
        }
        const previous = mode === 'concurrent' ? 8 : stock; stock = previous + body.delta
        return route.fulfill({ json: { variant_id: mode === 'mismatch' ? product : variant, previous_stock: previous, new_stock: stock, delta: body.delta, reason: body.reason } })
      }
      if (mode === 'denied') return route.fulfill({ status: 403, json: { error: { message: 'Inventory unavailable' } } })
      if (!path.endsWith('/inventory')) return route.fulfill({ json: mode === 'foreign' ? { ...row(), product_id: variant } : row() })
      const p = Number(url.searchParams.get('page') || 1), low = url.searchParams.get('low_stock_only') === 'true', q = url.searchParams.get('q')
      const filtered = mode === 'empty' || (low && !row().is_low_stock) || q === 'missing'
      const data = filtered ? [] : [row()]
      const total = filtered ? 0 : mode === 'pages' ? 21 : 1
      return route.fulfill({ json: { data, total, page: p, per_page: 20, pages: Math.ceil(total / 20) } })
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return { writes, reads }
}
const open = (page: Page) => page.goto('/seller/inventory')
async function editor(page: Page) { await page.getByRole('button', { name: 'Manage stock WHZ-TEST', exact: true }).click(); await expect(page.getByLabel('Quantity change', { exact: true })).toBeVisible() }
async function review(page: Page, delta = '5') { await page.getByLabel('Quantity change', { exact: true }).fill(delta); await page.getByLabel('Adjustment reason').fill('Restock delivery'); await page.getByRole('button', { name: 'Review stock change', exact: true }).click() }
test('shows reservation-aware stock and reviews one explicit adjustment', async ({ page }, info) => {
  const state = await setup(page); await open(page); await editor(page); await review(page)
  expect(state.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('seller-inventory.png'), fullPage: true })
  await page.getByRole('button', { name: 'Confirm stock change', exact: true }).dblclick()
  await expect(page.getByText('Stock adjustment saved: 10 → 15 units.', { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ method: 'POST', body: { delta: 5, reason: 'Restock delivery' } }])
})
test('sets physical count and changed threshold with confirmation', async ({ page }) => {
  const state = await setup(page); await open(page); await editor(page)
  await page.getByLabel('Stock action').selectOption('set'); await page.getByLabel('Total physical stock', { exact: true }).fill('20'); await page.getByLabel('Low-stock threshold', { exact: true }).fill('8')
  await page.getByRole('button', { name: 'Review stock change', exact: true }).click(); expect(state.writes).toEqual([])
  await page.getByRole('button', { name: 'Confirm stock change', exact: true }).click()
  await expect(page.getByText('Stock count saved: 20 units.', { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ method: 'PUT', body: { stock: 20, reorder_point: 8 } }])
})
test('accepts authoritative receipt after concurrent stock movement', async ({ page }) => {
  const state = await setup(page, 'concurrent'); await open(page); await editor(page); await review(page)
  await page.getByRole('button', { name: 'Confirm stock change', exact: true }).click()
  await expect(page.getByText('Stock adjustment saved: 8 → 13 units.', { exact: true })).toBeVisible(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['lost', 'mismatch']) test(`${mode} adjustment remains locked after refresh and reload`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await editor(page); await review(page)
  await page.getByRole('button', { name: 'Confirm stock change', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.getByRole('button', { name: 'Refresh inventory', exact: true }).click(); await expect(page.getByRole('button', { name: 'Manage stock WHZ-TEST', exact: true })).toBeDisabled()
  await page.reload(); await expect(page.getByRole('button', { name: 'Manage stock WHZ-TEST', exact: true })).toBeDisabled(); expect(state.writes).toHaveLength(1)
})
test('known rejection allows explicit correction without replay', async ({ page }) => {
  const state = await setup(page, 'rejected'); await open(page); await editor(page); await review(page)
  await page.getByRole('button', { name: 'Confirm stock change', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Stock cannot fall below reserved units'); await expect(page.getByRole('button', { name: 'Back to stock edits', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
test('local reserved-stock guard and closing the editor do not write', async ({ page }) => {
  const state = await setup(page); await open(page); await editor(page); await review(page, '-8')
  await expect(page.getByRole('alert')).toContainText('below the reserved quantity')
  await page.getByRole('button', { name: 'Close stock editor', exact: true }).click(); expect(state.writes).toEqual([])
})
test('search, low-stock filter and pagination use scoped reads', async ({ page }) => {
  const state = await setup(page, 'pages'); await open(page)
  await page.getByRole('button', { name: 'Next page', exact: true }).click(); await expect(page.getByText('Page 2 of 2', { exact: true })).toBeVisible()
  await page.getByLabel('Search products or SKU').fill('missing'); await page.getByRole('button', { name: 'Search inventory', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'No inventory on this page' })).toBeVisible(); await expect(page.getByRole('button', { name: 'Previous page', exact: true })).toBeDisabled()
  await page.getByLabel('Low stock only').check(); await expect(page.getByRole('heading', { name: 'No inventory on this page' })).toBeVisible()
  expect(state.reads.some((call) => call.includes('page=2'))).toBe(true); expect(state.reads.some((call) => call.includes('q=missing'))).toBe(true); expect(state.writes).toEqual([])
})
for (const mode of ['denied', 'foreign', 'inactive']) test(`${mode} does not allow stock changes`, async ({ page }) => {
  const state = await setup(page, mode); await open(page)
  if (mode === 'foreign') await page.getByRole('button', { name: 'Manage stock WHZ-TEST', exact: true }).click()
  await expect(page.getByText(mode === 'denied' ? 'Inventory unavailable' : mode === 'inactive' ? 'An active seller account is required to manage inventory.' : 'Inventory information could not be verified. Refresh and try again.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Quantity change', { exact: true })).toHaveCount(0); expect(state.writes).toEqual([])
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to manage inventory'], ['customer', true, 'A seller account is required'], ['admin', true, 'A seller account is required'], ['seller', false, 'Verify your email first']] as const) test(`${role} verified=${verified} is gated`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { name: heading })).toBeVisible(); expect(state.reads).toEqual([])
})
