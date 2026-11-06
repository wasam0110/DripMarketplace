import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111', seller = '22222222-2222-4222-8222-222222222222', other = '33333333-3333-4333-8333-333333333333', itemId = '44444444-4444-4444-8444-444444444444'
async function setup(page: Page, mode = 'ready', role = 'admin', verified = true) {
  const reads: string[] = [], writes: string[] = []; let denied = mode === 'denied'
  const row = () => ({ id, order_number: 'WHZ-2026-001', status: 'processing', customer_name: 'Snapshot Recipient', seller_count: 2, subtotal: '1700.55', total: '1800.75', commission: '150.06', payment_method: mode === 'legacy' ? 'card' : 'cod', created_at: '2026-10-28T00:00:00Z' })
  const detail = () => ({ ...row(), user_id: null, discount_amount: '100.05', shipping_fee: '200.25', notes: '<script>window.orderExecuted=true</script>Saved note', address: { recipient_name: 'Snapshot Recipient', phone: '03001234567', street: '1 Test Street', city: 'Lahore', province: 'Punjab', note: 'Saved delivery note' }, items: [{ id: itemId, seller_id: seller, product_id: id, variant_id: itemId, product_name: 'Saved linen shirt', variant_label: 'M / Ivory', quantity: 1, unit_price: '1000.25', subtotal: '1000.25' }, { id: other, seller_id: other, product_id: other, variant_id: other, product_name: 'Saved scarf', variant_label: 'Blue', quantity: 1, unit_price: '700.30', subtotal: '700.30' }], seller_orders: [{ id: itemId, seller_id: seller, brand_name: 'First Brand', status: 'processing', subtotal: '1000.25', tracking_number: null, courier_name: null, shipped_at: null, delivered_at: null }, { id: other, seller_id: other, brand_name: 'Second Brand', status: 'shipped', subtotal: '700.30', tracking_number: 'SAVED-TRACK', courier_name: 'Test Courier', shipped_at: '2026-10-28T00:00:00Z', delivered_at: null }] })
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'admin-owner', role, email: 'admin@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (!path.includes('/admin/orders')) return route.fulfill({ status: 404, json: {} })
    expect(route.request().headers().authorization).toBe('Bearer fixture-token')
    if (method !== 'GET') { writes.push(path); return route.fulfill({ status: 405, json: {} }) }
    reads.push(`${path}${url.search}`)
    if (denied || mode === 'missing') return route.fulfill({ status: mode === 'missing' ? 404 : 403, json: { error: { message: 'Order information unavailable' } } })
    if (path.endsWith('/admin/orders')) {
      const pageNumber = Number(url.searchParams.get('page') || 1), status = url.searchParams.get('status'), method = url.searchParams.get('payment_method')
      if (mode === 'slow' && status === 'shipped') await new Promise((resolve) => setTimeout(resolve, 500))
      const data = mode === 'empty' ? [] : [{ ...row(), id: pageNumber === 1 ? id : other, status: status || row().status, payment_method: method || row().payment_method, order_number: mode === 'slow' && status === 'shipped' ? 'Stale filtered order' : row().order_number }]
      return route.fulfill({ json: { data, totals: { total_gmv: '3302.30', total_commission: '150.06', order_count: mode === 'empty' ? 0 : 26 }, total: mode === 'empty' ? 0 : 26, page: pageNumber, per_page: 25, total_pages: mode === 'empty' ? 1 : 2 } })
    }
    return route.fulfill({ json: { ...detail(), ...(mode === 'wrong-id' ? { id: other } : {}), ...(mode === 'missing-commission' ? { commission: undefined } : {}), ...(mode === 'partial' ? { address: null, items: [], seller_orders: [] } : {}), ...(mode === 'inconsistent' ? { total: '999.99' } : {}) } })
  })
  return { reads, writes, allow: () => { denied = false } }
}
const open = (page: Page) => page.goto(`/admin/orders/${id}`)
test('list filters reset pages, preserve history and show full matching totals', async ({ page }, info) => {
  const state = await setup(page); await page.goto('/admin/orders'); await expect(page.getByRole('link', { name: 'Inspect WHZ-2026-001' })).toHaveAttribute('href', `/admin/orders/${id}`); await expect(page.getByText('PKR 3,302.30', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Next order page', exact: true }).click(); await expect(page.getByText('Page 2 of 2 · 26 matching orders', { exact: true })).toBeVisible()
  await page.getByLabel('Order status', { exact: true }).selectOption('processing'); await page.getByLabel('Payment method', { exact: true }).selectOption('cod'); await page.getByLabel('Seller reference (optional)', { exact: true }).fill(seller); await page.getByRole('button', { name: 'Apply order filters', exact: true }).click(); await expect(page.getByText('Page 1 of 2 · 26 matching orders', { exact: true })).toBeVisible(); expect(state.reads).toContain(`/api/v1/admin/orders?page=1&per_page=25&status=processing&payment_method=cod&seller_id=${seller}`)
  await page.goBack(); await expect(page.getByLabel('Order status', { exact: true })).toHaveValue('all'); await expect(page.getByLabel('Payment method', { exact: true })).toHaveValue('all'); await expect(page.getByLabel('Seller reference (optional)', { exact: true })).toHaveValue('')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]); expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('admin-order-list.png'), fullPage: true }); expect(state.writes).toEqual([])
})
test('private detail shows saved amounts, all brands and shipments without actions', async ({ page }, info) => {
  const state = await setup(page); await open(page); await expect(page.getByText('PKR 1,800.75', { exact: true })).toBeVisible(); await expect(page.getByRole('heading', { name: 'Saved linen shirt' })).toBeVisible(); await expect(page.getByRole('heading', { name: 'Saved scarf' })).toBeVisible(); await expect(page.getByText('SAVED-TRACK', { exact: true })).toBeVisible(); await expect(page.getByText('1 Test Street', { exact: false })).toBeVisible()
  await expect(page.getByRole('link', { name: `Inspect brand ${other}` })).toHaveAttribute('href', `/admin/sellers/${other}`); await expect(page.getByRole('link', { name: `Inspect current product ${id}` })).toHaveAttribute('href', `/admin/products/${id}`)
  expect(await page.evaluate(() => 'orderExecuted' in window)).toBe(false); expect(state.writes).toEqual([]); expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toMatch(/fixture-token|Snapshot Recipient|03001234567/)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]); expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('admin-order-detail.png'), fullPage: true }); await page.getByRole('button', { name: 'Refresh order detail', exact: true }).click(); await expect(page.getByRole('heading', { name: 'WHZ-2026-001' })).toBeVisible(); expect(state.writes).toEqual([])
})
test('partial historical snapshots show explicit warnings without fabricated data', async ({ page }) => {
  const state = await setup(page, 'partial'); await open(page); await expect(page.getByText('No saved delivery address.', { exact: true })).toBeVisible(); await expect(page.getByText('No saved item snapshots.', { exact: true })).toBeVisible(); await expect(page.getByText('No saved brand fulfilment records.', { exact: true })).toBeVisible(); await expect(page.getByRole('alert')).toHaveCount(3); expect(state.writes).toEqual([])
})
test('inconsistent checkout totals stay visible with an investigation warning', async ({ page }) => {
  const state = await setup(page, 'inconsistent'); await open(page); await expect(page.getByRole('alert')).toContainText('Saved checkout amounts do not reconcile'); await expect(page.getByText('PKR 999.99', { exact: true })).toBeVisible(); expect(state.writes).toEqual([])
})
test('historical payment methods remain readable without becoming filter options', async ({ page }) => {
  const state = await setup(page, 'legacy'); await open(page); await expect(page.getByText('Card (historical)', { exact: true })).toBeVisible(); await page.goto('/admin/orders'); await expect(page.getByLabel('Payment method', { exact: true }).locator('option')).toHaveCount(3); expect(state.writes).toEqual([])
})
for (const mode of ['wrong-id', 'missing-commission']) test(`${mode} prevents unverified order display`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await expect(page.getByRole('alert')).toContainText('could not be verified'); await expect(page.getByRole('heading', { name: 'WHZ-2026-001' })).toHaveCount(0); expect(state.writes).toEqual([])
})
for (const detail of [false, true]) test(`denied ${detail ? 'detail' : 'list'} can be retried`, async ({ page }) => {
  const state = await setup(page, 'denied'); if (detail) await open(page); else await page.goto('/admin/orders'); await expect(page.getByRole('alert')).toContainText('unavailable'); state.allow(); await page.getByRole('button', { name: detail ? 'Refresh order detail' : 'Refresh admin orders', exact: true }).click(); await expect(page.getByRole('heading', { name: 'WHZ-2026-001' })).toBeVisible(); expect(state.writes).toEqual([])
})
test('empty pages remain navigable without invented orders', async ({ page }) => {
  const state = await setup(page, 'empty'); await page.goto('/admin/orders'); await expect(page.getByText('No orders on this page', { exact: true })).toBeVisible(); await expect(page.getByRole('button', { name: 'Next order page', exact: true })).toBeDisabled(); expect(state.writes).toEqual([])
})
test('missing orders show the server error', async ({ page }) => { await setup(page, 'missing'); await open(page); await expect(page.getByRole('alert')).toContainText('unavailable') })
test('invalid filter edits never reach the API', async ({ page }) => {
  const state = await setup(page); await page.goto('/admin/orders'); await expect(page.getByRole('heading', { name: 'WHZ-2026-001' })).toBeVisible(); const count = state.reads.length; await page.getByLabel('Seller reference (optional)', { exact: true }).fill('invalid'); await page.getByRole('button', { name: 'Apply order filters', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('valid seller'); expect(state.reads).toHaveLength(count)
})
test('stale filtered responses do not replace the current list', async ({ page }) => {
  await setup(page, 'slow'); await page.goto('/admin/orders'); await page.getByLabel('Order status', { exact: true }).selectOption('shipped'); await page.getByRole('button', { name: 'Apply order filters', exact: true }).click(); await page.getByLabel('Order status', { exact: true }).selectOption('all'); await page.getByRole('button', { name: 'Apply order filters', exact: true }).click(); await expect(page.getByRole('heading', { name: 'WHZ-2026-001' })).toBeVisible(); await page.waitForTimeout(650); await expect(page.getByText('Stale filtered order', { exact: true })).toHaveCount(0)
})
for (const path of ['/admin/orders/invalid', '/admin/orders?status=unknown', '/admin/orders?seller_id=invalid', '/admin/orders?page=0', '/admin/orders?payment_method=card']) test(`${path} sends no admin reads`, async ({ page }) => {
  const state = await setup(page); await page.goto(path); await expect(page.getByRole('alert')).toBeVisible(); expect(state.reads).toEqual([])
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to inspect orders'], ['customer', true, 'An administrator account is required'], ['seller', true, 'An administrator account is required'], ['Admin', true, 'An administrator account is required'], ['admin', false, 'Verify your email first']] as const) test(`${role} verified=${verified} sends no admin reads`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading); expect(state.reads).toEqual([]); expect(state.writes).toEqual([])
})
