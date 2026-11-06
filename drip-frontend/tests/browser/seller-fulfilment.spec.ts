import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const seller = '11111111-1111-4111-8111-111111111111', parent = '22222222-2222-4222-8222-222222222222', id = '33333333-3333-4333-8333-333333333333'
async function setup(page: Page, mode = 'ready', role = 'seller', verified = true) {
  let status = ['processing', 'shipped', 'delivered', 'cancelled', 'unknown'].includes(mode) ? mode : 'pending'
  let tracking: string | null = null, courier: string | null = null
  const writes: Record<string, unknown>[] = [], reads: string[] = []
  const detail = () => ({ id: mode === 'foreign' ? parent : id, order_id: parent, order_number: 'WHZ-001', status, subtotal: '5000.00', tracking_number: tracking, courier_name: courier, shipped_at: null, delivered_at: null, created_at: '2026-10-28T10:00:00+00:00', shipping_address: { recipient_name: 'Test Customer', phone: '03001234567', street: mode === 'no-address' ? '' : 'Test Street', city: 'Lahore', province: 'Punjab', note: 'Ring the bell' }, items: [{ product_name: 'Linen shirt', variant_label: 'M · Blue', unit_price: '2500.00', quantity: 2, subtotal: '5000.00' }] })
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, email: 'seller@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.includes('/seller/')) reads.push(`${method} ${path}${url.search}`)
    if (path.endsWith('/seller/me')) return route.fulfill({ json: { id: seller, brand_name: 'Fixture Label', status: mode === 'inactive' ? 'suspended' : 'active', registration_amount_due: '0.00', registration_paid_at: null } })
    if (path.includes('/seller/orders')) {
      if (method === 'PUT') {
        expect(path).toBe(`/api/v1/seller/orders/${id}/status`); expect(route.request().headers().authorization).toBe('Bearer fixture-token')
        const body = route.request().postDataJSON(); writes.push(body)
        if (mode === 'rejected') return route.fulfill({ status: 400, json: { error: { message: 'The order must be paid or COD verified before fulfilment' } } })
        if (mode === 'lost') return route.abort()
        if (mode !== 'mismatch') { status = body.status; tracking = body.tracking_number ?? tracking; courier = body.courier_name ?? courier }
        return route.fulfill({ json: { message: 'Status updated' } })
      }
      if (mode === 'denied' || (mode === 'read-denied' && writes.length)) return route.fulfill({ status: 403, json: { error: { message: 'Order unavailable' } } })
      if (path.endsWith('/orders')) {
        const p = Number(url.searchParams.get('page') || 1), filter = url.searchParams.get('status')
        const data = mode === 'empty' || (filter !== 'all' && filter !== status) ? [] : [detail()]
        return route.fulfill({ json: { data, pagination: { page: p, per_page: 25, total: data.length ? mode === 'pages' ? 26 : 1 : 0, total_pages: data.length && mode === 'pages' ? 2 : 1 } } })
      }
      return route.fulfill({ json: detail() })
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return { writes, reads }
}
const open = (page: Page) => page.goto(`/seller/orders/${id}`)
async function review(page: Page) { await page.getByRole('button', { name: 'Review fulfilment update', exact: true }).click() }
test('shows own shipment details and confirms preparation', async ({ page }, info) => {
  const state = await setup(page); await open(page)
  await expect(page.getByRole('heading', { name: 'WHZ-001', exact: true })).toBeVisible()
  await expect(page.getByText('Test Customer', { exact: false })).toBeVisible()
  await review(page); expect(state.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('seller-fulfilment.png'), fullPage: true })
  await page.getByRole('button', { name: 'Confirm fulfilment update', exact: true }).dblclick()
  await expect(page.getByText('Fulfilment update saved and confirmed.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Tracking number', { exact: true })).toBeVisible(); expect(state.writes).toEqual([{ status: 'processing' }])
})
test('ships with tracking and courier then confirms delivery', async ({ page }) => {
  const state = await setup(page, 'processing'); await open(page)
  await page.getByLabel('Tracking number', { exact: true }).fill(' PK123 '); await page.getByLabel('Courier name', { exact: true }).fill(' Test Courier '); await review(page)
  await page.getByRole('button', { name: 'Confirm fulfilment update', exact: true }).click()
  await expect(page.getByText('Tracking number: PK123', { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ status: 'shipped', tracking_number: 'PK123', courier_name: 'Test Courier' }])
  await review(page); await expect(page.getByText(/Delivery can start the earnings settlement process/)).toBeVisible()
  await page.getByRole('button', { name: 'Confirm fulfilment update', exact: true }).click()
  await expect(page.getByText('No fulfilment action is available for this order.', { exact: true })).toBeVisible(); expect(state.writes[1]).toEqual({ status: 'delivered' })
})
for (const mode of ['lost', 'mismatch', 'read-denied']) test(`${mode} update blocks replay after refresh and reload`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page)
  await page.getByRole('button', { name: 'Confirm fulfilment update', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.getByRole('button', { name: 'Refresh fulfilment and discard edits' }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.reload(); await expect(page.getByText(/A fulfilment update is awaiting confirmation/)).toBeVisible(); expect(state.writes).toHaveLength(1)
  await expect(page.getByRole('button', { name: 'Confirm fulfilment update', exact: true })).toHaveCount(0)
})
test('unpaid or unverified COD rejection permits correction without replay', async ({ page }) => {
  const state = await setup(page, 'rejected'); await open(page); await review(page)
  await page.getByRole('button', { name: 'Confirm fulfilment update', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('paid or COD verified'); await expect(page.getByRole('button', { name: 'Back to fulfilment edits', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
test('review cancellation and invalid tracking never write', async ({ page }) => {
  const state = await setup(page, 'processing'); await open(page)
  await page.getByLabel('Tracking number', { exact: true }).fill('   '); await review(page); await expect(page.getByRole('alert')).toContainText('Enter a tracking number')
  await page.getByLabel('Tracking number', { exact: true }).fill('PK123'); await review(page)
  await page.getByRole('button', { name: 'Back to fulfilment edits', exact: true }).click(); expect(state.writes).toEqual([])
})
test('queue filters and paginates scoped seller orders', async ({ page }) => {
  const state = await setup(page, 'pages'); await page.goto('/seller/orders')
  await page.getByRole('button', { name: 'Next page', exact: true }).click(); await expect(page.getByText('Page 2 of 2', { exact: true })).toBeVisible()
  await page.getByLabel('Fulfilment status').selectOption('shipped'); await expect(page.getByRole('heading', { name: 'No seller orders on this page' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Previous page', exact: true })).toBeDisabled(); expect(state.writes).toEqual([])
  expect(state.reads.some((path) => path.includes('status=shipped&page=1'))).toBe(true)
})
for (const mode of ['delivered', 'cancelled', 'unknown']) test(`${mode} has no transition action`, async ({ page }) => {
  await setup(page, mode); await open(page); await expect(page.getByText('No fulfilment action is available for this order.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Review fulfilment update', exact: true })).toHaveCount(0)
})
test('incomplete shipping data blocks actions', async ({ page }) => {
  await setup(page, 'no-address'); await open(page); await expect(page.getByRole('alert')).toContainText('delivery address is incomplete'); await expect(page.getByRole('button', { name: 'Review fulfilment update', exact: true })).toBeDisabled()
})
for (const mode of ['foreign', 'denied', 'inactive']) test(`${mode} cannot access fulfilment actions`, async ({ page }) => {
  await setup(page, mode); await open(page)
  await expect(page.getByText(mode === 'foreign' ? 'The fulfilment order could not be verified. Refresh to try again.' : mode === 'denied' ? 'Order unavailable' : 'An active seller account is required to manage fulfilment.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Review fulfilment update', exact: true })).toHaveCount(0)
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to manage fulfilment'], ['customer', true, 'A seller account is required'], ['admin', true, 'A seller account is required'], ['seller', false, 'Verify your email first']] as const) test(`${role} verified=${verified} is gated`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { name: heading })).toBeVisible(); expect(state.reads).toEqual([])
})
