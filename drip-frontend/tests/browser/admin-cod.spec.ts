import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111', seller = '22222222-2222-4222-8222-222222222222'
async function setup(page: Page, mode = 'ready', role = 'admin', verified = true) {
  const writes: { path: string; body: unknown }[] = [], reads: string[] = []
  const placed = new Date(Date.now() - (mode === 'expired' ? 60 : 5)*60000).toISOString()
  let expires = new Date(Date.parse(placed)+30*60000).toISOString(), status = 'pending_cod_verification', note = 'Saved order note', updated = placed, denied = mode === 'denied'
  const queue = () => ({ order_id: id, order_number: 'WHZ-COD-001', customer_name: 'Snapshot Recipient', customer_phone: '03001234567', total: '1200.25', brand_names: ['Fixture Brand'], placed_at: placed, expires_at: expires, updated_at: updated, minutes_remaining: mode === 'expired' ? 0 : 24 })
  const order = () => ({ id, order_number: 'WHZ-COD-001', status, payment_method: 'cod', customer_name: 'Snapshot Recipient', user_id: null, commission: '0', subtotal: '1000.25', discount_amount: '0', shipping_fee: '200', total: '1200.25', notes: note, created_at: placed, address: { recipient_name: 'Snapshot Recipient', phone: '03001234567', street: '1 Test Street', city: 'Lahore', province: 'Punjab', note: 'Saved delivery note' }, items: [{ id, seller_id: seller, product_id: id, variant_id: id, product_name: 'Saved linen shirt', variant_label: 'M / Ivory', quantity: 1, unit_price: '1000.25', subtotal: '1000.25' }], seller_orders: [{ id, seller_id: seller, brand_name: 'Fixture Brand', status: status === 'cancelled' ? 'cancelled' : 'pending', subtotal: '1000.25', tracking_number: null, courier_name: null, shipped_at: null, delivered_at: null }] })
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'admin-owner', role, email: 'admin@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (!path.includes('/admin/cod-queue') && !path.includes('/admin/orders/')) return route.fulfill({ status: 404, json: {} })
    expect(route.request().headers().authorization).toBe('Bearer fixture-token')
    if (method === 'POST') {
      writes.push({ path, body: route.request().postDataJSON() })
      if (mode === 'rejection' || mode === 'conflict') return route.fulfill({ status: mode === 'conflict' ? 409 : 422, json: { error: { message: 'Refresh and inspect the COD order.' } } })
      status = path.endsWith('/verify') ? 'processing' : 'cancelled'
      if (mode === 'lost') return route.abort()
      return route.fulfill({ json: { order_id: mode === 'wrong-receipt' ? seller : id, order_number: 'WHZ-COD-001', status, message: 'Decision recorded' } })
    }
    reads.push(path)
    if (denied || (mode === 'readback-denied' && writes.length && path.includes('/admin/orders/'))) return route.fulfill({ status: 403, json: { error: { message: 'COD information unavailable' } } })
    if (path.endsWith('/cod-queue')) return route.fulfill({ json: mode === 'empty' || status !== 'pending_cod_verification' ? [] : [{ ...queue(), ...(mode === 'missing-version' ? { updated_at: undefined } : {}) }] })
    return route.fulfill({ json: { ...order(), ...(mode === 'wrong-order' ? { id: seller } : {}), ...(mode === 'wrong-method' ? { payment_method: 'payfast' } : {}), ...(mode === 'readback-mismatch' && writes.length ? { status: 'pending_cod_verification' } : {}) } })
  })
  return { writes, reads, allow: () => { denied = false }, queue, change: (kind: string) => { if (kind === 'deadline') expires = new Date(Date.parse(expires)+60000).toISOString(); if (kind === 'version') updated = new Date(Date.parse(updated)+1000).toISOString(); if (kind === 'content') note = 'Changed note'; if (kind === 'status') status = 'processing' } }
}
const open = (page: Page) => page.goto(`/admin/cod/${id}`)
async function review(page: Page, action = 'verify') { await page.getByLabel('Action', { exact: true }).selectOption(action); if (action === 'cancel') await page.getByLabel('Cancellation reason', { exact: true }).fill('Customer asked to cancel the order'); else await page.getByLabel('Approval note (optional)', { exact: true }).fill('Customer contacted and checked'); await page.getByRole('checkbox').check(); await page.getByRole('button', { name: 'Review COD action', exact: true }).click() }
test('queue is private, accessible and links to the correct review', async ({ page }, info) => {
  const state = await setup(page); await page.goto('/admin/cod'); await expect(page.getByRole('link', { name: 'Review COD WHZ-COD-001' })).toHaveAttribute('href', `/admin/cod/${id}`)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]); expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true); await page.getByRole('heading', { level: 1 }).click(); await page.screenshot({ path: info.outputPath('admin-cod-queue.png'), fullPage: true }); expect(state.writes).toEqual([])
})
test('approval is reviewed once, versioned and confirmed without claiming payment', async ({ page }, info) => {
  const state = await setup(page); await open(page); await review(page); expect(state.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]); expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true); await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('admin-cod-review.png'), fullPage: true })
  await page.getByRole('button', { name: 'Confirm COD action', exact: true }).dblclick(); await expect(page.getByText('COD order approved for preparation. No payment collection was recorded.', { exact: true })).toBeVisible(); expect(state.writes).toHaveLength(1); expect(state.writes[0].body).toEqual({ note: 'Customer contacted and checked', expected_updated_at: state.queue().updated_at, expected_expires_at: state.queue().expires_at }); await expect(page.getByText('This order is no longer in the COD queue.', { exact: true })).toBeVisible(); expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toMatch(/fixture-token|03001234567|Customer contacted/)
})
test('cancellation can be abandoned and then confirmed once', async ({ page }) => {
  const state = await setup(page); await open(page); await review(page, 'cancel'); await page.getByRole('button', { name: 'Back to COD decision', exact: true }).click(); expect(state.writes).toEqual([]); await review(page, 'cancel'); await page.getByRole('button', { name: 'Confirm COD action', exact: true }).dblclick(); await expect(page.getByText('COD order cancellation confirmed. No refund was issued.', { exact: true })).toBeVisible(); expect(state.writes).toHaveLength(1); expect(state.writes[0].path).toMatch(/\/cancel$/)
})
test('expired orders cannot be approved but can be reviewed for cancellation', async ({ page }) => {
  const state = await setup(page, 'expired'); await open(page); await expect(page.getByRole('option', { name: 'Approve for preparation' })).toBeDisabled(); await expect(page.getByRole('alert')).toContainText('deadline has expired'); await review(page, 'cancel'); await page.getByRole('button', { name: 'Confirm COD action', exact: true }).click(); await expect(page.getByText('COD order cancellation confirmed. No refund was issued.', { exact: true })).toBeVisible(); expect(state.writes).toHaveLength(1)
})
for (const kind of ['deadline', 'version', 'content', 'status']) test(`changed ${kind} prevents preflight writes`, async ({ page }) => {
  const state = await setup(page); await open(page); await review(page); state.change(kind); await page.getByRole('button', { name: 'Confirm COD action', exact: true }).click(); await expect(page.getByRole('alert').first()).toBeVisible(); expect(state.writes).toEqual([])
})
for (const mode of ['lost', 'wrong-receipt', 'readback-denied', 'readback-mismatch']) test(`${mode} locks actions across reload`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm COD action', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); await page.reload(); await expect(page.getByText(/A COD action is awaiting confirmation/)).toBeVisible(); await page.getByRole('button', { name: 'Refresh COD review and discard decision', exact: true }).click(); await expect(page.getByText(/A COD action is awaiting confirmation/)).toBeVisible(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['rejection', 'conflict']) test(`${mode} permits correction without auto replay`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm COD action', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('Refresh and inspect'); await expect(page.getByRole('button', { name: 'Back to COD decision', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
test('confirmation and a clear cancellation reason are required locally', async ({ page }) => {
  const state = await setup(page); await open(page); await page.getByRole('button', { name: 'Review COD action', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('Confirm the reviewed action'); await page.getByLabel('Action', { exact: true }).selectOption('cancel'); await page.getByRole('checkbox').check(); await page.getByLabel('Cancellation reason', { exact: true }).fill('short'); await page.getByRole('button', { name: 'Review COD action', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('10–500'); expect(state.writes).toEqual([])
})
for (const mode of ['wrong-order', 'wrong-method', 'missing-version']) test(`${mode} prevents decisions`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await expect(page.getByRole('alert')).toContainText('could not be verified'); await expect(page.getByRole('button', { name: 'Review COD action', exact: true })).toHaveCount(0); expect(state.writes).toEqual([])
})
test('empty queue is explicit and a departed order has no action form', async ({ page }) => {
  const state = await setup(page, 'empty'); await page.goto('/admin/cod'); await expect(page.getByText('No orders awaiting COD verification', { exact: true })).toBeVisible(); await open(page); await expect(page.getByText('This order is no longer in the COD queue.', { exact: true })).toBeVisible(); await expect(page.getByRole('button', { name: 'Review COD action', exact: true })).toHaveCount(0); expect(state.writes).toEqual([])
})
test('denied queue can be retried', async ({ page }) => {
  const state = await setup(page, 'denied'); await page.goto('/admin/cod'); await expect(page.getByRole('alert')).toContainText('unavailable'); state.allow(); await page.getByRole('button', { name: 'Refresh COD queue', exact: true }).click(); await expect(page.getByRole('link', { name: 'Review COD WHZ-COD-001' })).toBeVisible(); expect(state.writes).toEqual([])
})
test('invalid order reference sends no protected reads', async ({ page }) => { const state = await setup(page); await page.goto('/admin/cod/invalid'); await expect(page.getByRole('alert')).toContainText('invalid'); expect(state.reads).toEqual([]) })
for (const [role, verified, heading] of [['guest', true, 'Sign in to review COD orders'], ['customer', true, 'An administrator account is required'], ['seller', true, 'An administrator account is required'], ['Admin', true, 'An administrator account is required'], ['admin', false, 'Verify your email first']] as const) test(`${role} verified=${verified} has no protected actions`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading); expect(state.reads).toEqual([]); expect(state.writes).toEqual([])
})
