import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const seller = '11111111-1111-4111-8111-111111111111', parent = '22222222-2222-4222-8222-222222222222', shipment = '33333333-3333-4333-8333-333333333333', id = '44444444-4444-4444-8444-444444444444', item = '55555555-5555-4555-8555-555555555555'
async function setup(page: Page, mode = 'ready', role = 'seller', verified = true) {
  let status = ['approved', 'received', 'refunded', 'rejected', 'unknown'].includes(mode) ? mode : 'requested', notes = 'Original return notes'
  const writes: { path: string; body: Record<string, unknown> }[] = [], reads: string[] = []
  const actions = () => mode === 'no-actions' ? [] : mode === 'unknown' ? ['approve', 'request_refund'] : status === 'requested' ? ['approve', 'reject'] : status === 'approved' ? ['mark_received'] : []
  const detail = () => ({ id: mode === 'foreign' ? parent : id, order_id: parent, seller_order_id: shipment, status, reason: 'The item does not fit.', item_count: 1, requested_at: '2026-10-28T10:00:00Z', resolved_at: null, notes, order_number: 'WHZ-001', items: [{ id: item, order_item_id: parent, product_id: seller, variant_id: shipment, product_name: 'Linen shirt', variant_label: 'M · Blue', unit_price: '2500.00', purchased_quantity: 2, requested_quantity: 1, line_subtotal: '2500.00', reason: null }], estimated_refund_amount: '2250.00', available_actions: actions(), refund_status: status === 'refunded' ? 'completed' : mode === 'refund-pending' ? 'pending' : null, dispute_status: mode === 'dispute' ? 'under_review' : null })
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, email: 'seller@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.includes('/seller/')) reads.push(`${method} ${path}${url.search}`)
    if (path.endsWith('/seller/me')) return route.fulfill({ json: { id: seller, brand_name: 'Fixture Label', status: mode === 'inactive' ? 'suspended' : 'active', registration_amount_due: '0.00', registration_paid_at: null } })
    if (path.includes('/seller/returns')) {
      if (method === 'POST') {
        const body = route.request().postDataJSON(); writes.push({ path, body })
        expect(route.request().headers().authorization).toBe('Bearer fixture-token')
        if (mode === 'lost') return route.abort()
        if (mode === 'conflict') return route.fulfill({ status: 400, json: { error: { message: 'Can only approve requested returns' } } })
        if (mode !== 'mismatch') {
          status = path.endsWith('/approve') ? 'approved' : path.endsWith('/reject') ? 'rejected' : 'received'
          if (body.admin_note) notes = body.admin_note
        }
        return route.fulfill({ json: { message: 'Updated' } })
      }
      if (mode === 'denied' || (mode === 'read-denied' && writes.length)) return route.fulfill({ status: 403, json: { error: { message: 'Return unavailable' } } })
      if (path.endsWith('/returns')) {
        const p = Number(url.searchParams.get('page') || 1), filter = url.searchParams.get('status'), data = mode === 'empty' || (filter && filter !== status) ? [] : [detail()]
        return route.fulfill({ json: { data, total: data.length ? mode === 'pages' ? 26 : 1 : 0, page: p, total_pages: data.length && mode === 'pages' ? 2 : 1 } })
      }
      return route.fulfill({ json: detail() })
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return { writes, reads }
}
const open = (page: Page) => page.goto(`/seller/returns/${id}`)
async function review(page: Page) { await page.getByRole('button', { name: 'Review return update', exact: true }).click() }
test('shows partial items and refund estimate, approves then marks receipt', async ({ page }, info) => {
  const state = await setup(page); await open(page)
  await expect(page.getByRole('heading', { name: 'Linen shirt', exact: true })).toBeVisible(); await expect(page.getByText('Estimated refund: PKR 2,250', { exact: true })).toBeVisible()
  await page.getByLabel('Decision note (optional)').fill('Return accepted'); await review(page); expect(state.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('seller-returns.png'), fullPage: true })
  await page.getByRole('button', { name: 'Confirm return update', exact: true }).dblclick(); await expect(page.getByText('Return update saved and confirmed.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Return action')).toHaveValue('mark_received')
  expect(state.writes).toEqual([{ path: `/api/v1/seller/returns/${id}/approve`, body: { admin_note: 'Return accepted' } }])
  await review(page); await page.getByRole('button', { name: 'Confirm return update', exact: true }).click()
  await expect(page.getByText('Item receipt is recorded. A completed refund is confirmed separately.', { exact: true })).toBeVisible()
  expect(state.writes[1]).toEqual({ path: `/api/v1/seller/returns/${id}/received`, body: {} })
  await expect(page.getByText('Refund: No refund recorded', { exact: true })).toBeVisible()
})
test('rejects with a note after explicit review', async ({ page }) => {
  const state = await setup(page); await open(page); await page.getByLabel('Return action').selectOption('reject'); await page.getByLabel('Decision note (optional)').fill('Outside the stated return policy.'); await review(page)
  await page.getByRole('button', { name: 'Confirm return update', exact: true }).click(); await expect(page.getByText('No seller action is currently available for this return.', { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ path: `/api/v1/seller/returns/${id}/reject`, body: { admin_note: 'Outside the stated return policy.' } }])
})
test('blank note preserves saved notes and backing out sends no action', async ({ page }) => {
  const state = await setup(page); await open(page); await review(page); await page.getByRole('button', { name: 'Back to return edits', exact: true }).click(); expect(state.writes).toEqual([])
  await review(page); await page.getByRole('button', { name: 'Confirm return update', exact: true }).click()
  await expect(page.getByLabel('Return action')).toHaveValue('mark_received'); await expect(page.getByText('Original return notes', { exact: true })).toBeVisible(); expect(state.writes[0].body).toEqual({})
})
for (const mode of ['lost', 'mismatch', 'read-denied']) test(`${mode} response remains locked after refresh and reload`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page)
  await page.getByRole('button', { name: 'Confirm return update', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.getByRole('button', { name: 'Refresh return and discard edits' }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.reload(); await expect(page.getByText(/A return update is awaiting confirmation/)).toBeVisible(); expect(state.writes).toHaveLength(1)
  await expect(page.getByRole('button', { name: 'Confirm return update', exact: true })).toHaveCount(0)
})
test('state rejection permits explicit refresh without automatic retry', async ({ page }) => {
  const state = await setup(page, 'conflict'); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm return update', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Can only approve requested returns'); await expect(page.getByRole('button', { name: 'Back to return edits', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
test('queue uses seller pagination and sends no all-status parameter', async ({ page }) => {
  const state = await setup(page, 'pages'); await page.goto('/seller/returns')
  await page.getByRole('button', { name: 'Next page', exact: true }).click(); await expect(page.getByText('Page 2 of 2', { exact: true })).toBeVisible()
  await page.getByLabel('Return status', { exact: true }).selectOption('received'); await expect(page.getByRole('heading', { name: 'No seller returns on this page' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Previous page', exact: true })).toBeDisabled(); expect(state.writes).toEqual([]); expect(state.reads.some((call) => call.includes('status=all'))).toBe(false)
})
for (const mode of ['received', 'refunded', 'rejected', 'unknown', 'no-actions']) test(`${mode} has no seller mutation action`, async ({ page }) => {
  await setup(page, mode); await open(page); await expect(page.getByText('No seller action is currently available for this return.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Review return update', exact: true })).toHaveCount(0)
})
test('displays dispute status without offering customer or admin dispute writes', async ({ page }) => {
  const state = await setup(page, 'dispute'); await open(page); await expect(page.getByText('Dispute: Under review', { exact: true })).toBeVisible(); expect(state.writes).toEqual([])
  await expect(page.getByRole('link', { name: 'View brand fulfilment' })).toHaveAttribute('href', `/seller/orders/${shipment}`)
})
for (const mode of ['foreign', 'denied', 'inactive']) test(`${mode} cannot update a return`, async ({ page }) => {
  await setup(page, mode); await open(page)
  await expect(page.getByText(mode === 'foreign' ? 'The seller return details could not be verified. Refresh to try again.' : mode === 'denied' ? 'Return unavailable' : 'An active seller account is required to manage returns.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Review return update', exact: true })).toHaveCount(0)
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to manage returns'], ['customer', true, 'A seller account is required'], ['admin', true, 'A seller account is required'], ['seller', false, 'Verify your email first']] as const) test(`${role} verified=${verified} is gated`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { name: heading })).toBeVisible(); expect(state.reads).toEqual([])
})
