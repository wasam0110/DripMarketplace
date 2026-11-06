import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111', owner = '22222222-2222-4222-8222-222222222222', other = '33333333-3333-4333-8333-333333333333'
async function setup(page: Page, mode = 'ready', role = 'admin', verified = true) {
  const writes: { path: string; body: unknown }[] = [], reads: string[] = []
  let status = mode === 'collected' ? 'completed' : 'pending', amount = '1200.25', version = '2026-11-01T01:00:00Z', orderStatus = mode === 'undelivered' ? 'shipped' : 'delivered', denied = mode === 'denied'
  const row = (paymentId = id) => ({ id: paymentId, order_id: other, order_number: 'WHZ-CASH-001', method: mode === 'payfast' ? 'payfast' : mode === 'historical' ? 'card' : 'cod', status, amount, currency: mode === 'currency' ? 'USD' : 'PKR', gateway_reference: status === 'completed' ? 'RECEIPT-001' : null, paid_at: status === 'completed' ? '2026-11-01T02:00:00Z' : null, created_at: '2026-11-01T00:00:00Z' })
  const detail = () => { const value = row(), eligible = value.method === 'cod' && value.currency === 'PKR' && status === 'pending' && orderStatus === 'delivered'; return { ...value, order_status: orderStatus, order_updated_at: version, can_record_cod_collection: eligible, collection_blockers: eligible ? [] : ['Collection is unavailable for this saved payment or delivery state.'], collection_recorded_by: status === 'completed' ? owner : null } }
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: owner, role, email: 'admin@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (!path.includes('/payments')) return route.fulfill({ status: 404, json: {} })
    expect(route.request().headers().authorization).toBe('Bearer fixture-token')
    if (method === 'POST') {
      writes.push({ path, body: route.request().postDataJSON() })
      if (mode === 'rejection' || mode === 'conflict') return route.fulfill({ status: mode === 'conflict' ? 409 : 422, json: { error: { message: 'Refresh and inspect the collection evidence.' } } })
      status = 'completed'
      if (mode === 'lost') return route.abort()
      return route.fulfill({ json: { payment_id: mode === 'wrong-receipt' ? other : id, order_id: other, order_number: 'WHZ-CASH-001', status, amount, currency: 'PKR', reference: 'RECEIPT-001', paid_at: '2026-11-01T02:00:00Z', recorded_by: owner } })
    }
    reads.push(`${path}${url.search}`)
    if (denied || (mode === 'readback-denied' && writes.length)) return route.fulfill({ status: 403, json: { error: { message: 'Payment information unavailable' } } })
    if (path.endsWith('/payments')) {
      const number = Number(url.searchParams.get('page') || 1), total = mode === 'empty' ? 0 : 26
      return route.fulfill({ json: { data: total ? [{ ...row(number === 1 ? id : other), status: url.searchParams.get('status') || status, method: url.searchParams.get('method') || 'cod' }] : [], total, page: number, per_page: 25, total_pages: total ? 2 : 1 } })
    }
    return route.fulfill({ json: { ...detail(), ...(mode === 'wrong-id' ? { id: other } : {}), ...(mode === 'missing-currency' ? { currency: undefined } : {}), ...(mode === 'missing-eligibility' ? { can_record_cod_collection: undefined } : {}), ...(mode === 'readback-mismatch' && writes.length ? { gateway_reference: 'OTHER-RECEIPT' } : {}) } })
  })
  return { writes, reads, allow: () => { denied = false }, change: (kind: string) => { if (kind === 'amount') amount = '1200.26'; if (kind === 'version') version = '2026-11-01T01:01:00Z'; if (kind === 'delivery') orderStatus = 'shipped' } }
}
const open = (page: Page) => page.goto(`/admin/payments/${id}`)
async function review(page: Page) { await page.getByLabel('Collection receipt reference', { exact: true }).fill('RECEIPT-001'); await page.getByRole('checkbox').check(); await page.getByRole('button', { name: 'Review cash collection', exact: true }).click() }
test('private payment filters and pagination preserve history without inventing revenue', async ({ page }, info) => {
  const state = await setup(page); await page.goto('/admin/payments'); await expect(page.getByRole('link', { name: 'Inspect payment WHZ-CASH-001' })).toHaveAttribute('href', `/admin/payments/${id}`); await page.getByRole('button', { name: 'Next payment page', exact: true }).click(); await expect(page.getByText('Page 2 of 2 · 26 matching payments', { exact: true })).toBeVisible()
  await page.getByLabel('Payment status', { exact: true }).selectOption('completed'); await page.getByLabel('Payment method', { exact: true }).selectOption('payfast'); await page.getByRole('button', { name: 'Apply payment filters', exact: true }).click(); await expect(page.getByText('Page 1 of 2 · 26 matching payments', { exact: true })).toBeVisible(); expect(state.reads).toContain('/api/v1/payments?page=1&status=completed&method=payfast'); await page.goBack(); await expect(page.getByLabel('Payment status', { exact: true })).toHaveValue('pending')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]); expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true); await page.getByRole('heading', { level: 1 }).click(); await page.screenshot({ path: info.outputPath('admin-payment-list.png'), fullPage: true }); expect(state.writes).toEqual([])
})
test('reviewed collection is submitted once and confirmed by saved evidence', async ({ page }, info) => {
  const state = await setup(page); await open(page); await review(page); expect(state.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]); expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true); await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('admin-payment-review.png'), fullPage: true })
  await page.getByRole('button', { name: 'Confirm cash collection', exact: true }).dblclick(); await expect(page.getByText('COD collection recorded and saved payment evidence confirmed. No seller payout was made.', { exact: true })).toBeVisible(); expect(state.writes).toHaveLength(1); expect(state.writes[0]).toEqual({ path: `/api/v1/payments/${id}/cod-collection`, body: { reference: 'RECEIPT-001', expected_amount: '1200.25', expected_order_updated_at: '2026-11-01T01:00:00Z' } }); await expect(page.getByRole('button', { name: 'Review cash collection' })).toHaveCount(0); expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toMatch(/fixture-token|RECEIPT-001/)
})
test('draft can be abandoned and requires explicit receipt confirmation', async ({ page }) => {
  const state = await setup(page); await open(page); await page.getByRole('button', { name: 'Review cash collection', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('Confirm receipt'); await review(page); await page.getByRole('button', { name: 'Back to collection draft', exact: true }).click(); await expect(page.getByRole('button', { name: 'Confirm cash collection', exact: true })).toHaveCount(0); expect(state.writes).toEqual([])
})
for (const kind of ['amount', 'version', 'delivery']) test(`changed ${kind} prevents preflight collection`, async ({ page }) => {
  const state = await setup(page); await open(page); await review(page); state.change(kind); await page.getByRole('button', { name: 'Confirm cash collection', exact: true }).click(); await expect(page.getByRole('alert').first()).toBeVisible(); expect(state.writes).toEqual([])
})
for (const mode of ['lost', 'wrong-receipt', 'readback-denied', 'readback-mismatch']) test(`${mode} locks collection across reload and refresh`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm cash collection', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); await page.reload(); await expect(page.getByText(/A collection is awaiting confirmation/)).toBeVisible(); await page.getByRole('button', { name: 'Refresh payment and discard collection draft', exact: true }).click(); await expect(page.getByText(/A collection is awaiting confirmation/)).toBeVisible(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['rejection', 'conflict']) test(`${mode} allows correction without automatic replay`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm cash collection', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('Refresh and inspect'); await expect(page.getByRole('button', { name: 'Back to collection draft', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['undelivered', 'payfast', 'historical', 'currency', 'collected']) test(`${mode} has no collection form`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await expect(page.getByRole('heading', { name: 'Collection eligibility and evidence' })).toBeVisible(); await expect(page.getByRole('button', { name: 'Review cash collection' })).toHaveCount(0); expect(state.writes).toEqual([])
})
for (const mode of ['wrong-id', 'missing-currency', 'missing-eligibility']) test(`${mode} blocks unverified payment content`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await expect(page.getByRole('alert')).toContainText('could not be verified'); await expect(page.getByRole('button', { name: 'Review cash collection' })).toHaveCount(0); expect(state.writes).toEqual([])
})
test('empty and denied lists are explicit and retryable', async ({ page }) => {
  const state = await setup(page, 'denied'); await page.goto('/admin/payments'); await expect(page.getByRole('alert')).toContainText('unavailable'); state.allow(); await page.getByRole('button', { name: 'Refresh payments', exact: true }).click(); await expect(page.getByRole('link', { name: 'Inspect payment WHZ-CASH-001' })).toBeVisible(); expect(state.writes).toEqual([])
})
test('empty list and invalid payment reference never invent actions', async ({ page }) => {
  const state = await setup(page, 'empty'); await page.goto('/admin/payments'); await expect(page.getByText('No payments on this page', { exact: true })).toBeVisible(); state.reads.length = 0; await page.goto('/admin/payments/invalid'); await expect(page.getByRole('alert')).toContainText('invalid'); expect(state.reads).toEqual([])
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to inspect payments'], ['customer', true, 'An administrator account is required'], ['seller', true, 'An administrator account is required'], ['Admin', true, 'An administrator account is required'], ['admin', false, 'Verify your email first']] as const) test(`${role} verified=${verified} cannot inspect or collect`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading); expect(state.reads).toEqual([]); expect(state.writes).toEqual([])
})
