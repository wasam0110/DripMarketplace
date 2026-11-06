import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { returned, disputed, rid, did, owner, other, when } from '../fixtures/admin-returns'

async function setup(page: Page, mode = 'ready', status = 'requested', role = 'admin', verified = true) {
  let r = returned(status), d = disputed(), denied = mode === 'denied'
  if (mode === 'closed') { d.status = 'resolved_seller'; d.resolved_at = when; d.resolution_note = 'Evidence supports seller' }
  if (mode === 'currency') r.order.payment_currency = 'USD'
  const writes: { path: string; body: Record<string, unknown> }[] = [], reads: string[] = []
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname, url = new URL(route.request().url()), method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: owner, role, email: 'admin@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (!path.includes('/admin/returns') && !path.includes('/admin/disputes')) return route.fulfill({ json: { data: [], total: 0 } })
    if (method === 'GET') {
      reads.push(path)
      if (denied || mode === 'readback-denied' && writes.length) return route.fulfill({ status: 403, json: { error: { message: 'Record unavailable', code: 'FORBIDDEN' } } })
      if (path.endsWith('/returns') || path.endsWith('/disputes')) { const row = path.endsWith('/returns') ? r : d, filter = url.searchParams.get('status'), p = Number(url.searchParams.get('page') || 1), empty = mode === 'empty' || filter && row.status !== filter; return route.fulfill({ json: { data: empty ? [] : [{ ...row, id: p === 2 ? other : row.id }], total: empty ? 0 : 26, page: p, total_pages: empty ? 1 : 2 } }) }
      const value = path.includes('/disputes/') ? d : r
      return route.fulfill({ json: mode === 'malformed' ? { ...value, id: other } : value })
    }
    const body = route.request().postDataJSON(); writes.push({ path, body })
    if (mode === 'lost') return route.abort('failed')
    if (mode === 'conflict') return route.fulfill({ status: 409, json: { error: { message: 'Refresh and inspect the changed record', code: 'CONFLICT' } } })
    if (path.includes('/returns/')) {
      const action = path.split('/').pop()
      if (action === 'refund') { r.refund = { refund_id: other, status: 'pending', amount: r.estimated_refund_amount, transfer_reference: null, requested_at: when, processed_at: null }; r.available_actions = []; return route.fulfill({ json: { refund_id: mode === 'wrong-receipt' ? did : other, status: 'pending' } }) }
      if (mode !== 'mismatch') { r.status = action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'received'; r.available_actions = []; r.notes = body.admin_note ?? r.notes }
      return route.fulfill({ json: { message: 'Saved' } })
    }
    if (path.endsWith('/messages')) { const msg = { id: rid, sender_id: owner, body: body.body, created_at: when }; if (mode !== 'mismatch') { d.messages.push(msg); d.status = 'under_review' }; return route.fulfill({ status: 201, json: mode === 'wrong-receipt' ? { ...msg, sender_id: other } : msg }) }
    d.status = `resolved_${body.in_favor_of}`; d.resolved_at = when; d.resolution_note = body.resolution_note
    if (body.in_favor_of === 'customer') { r = returned('approved'); r.dispute = { dispute_id: did, status: d.status } }
    return route.fulfill({ json: mode === 'wrong-receipt' ? { ...d, id: other } : d })
  })
  return { writes, reads, change: () => { r.notes = 'Updated by another administrator'; d.messages.push({ id: rid, sender_id: other, body: 'New evidence', created_at: when }) }, allow: () => { denied = false } }
}
async function review(page: Page, dispute = false, kind = 'message') {
  if (dispute) { await page.getByLabel('Action', { exact: true }).selectOption(kind); await page.getByLabel('Message or resolution note').fill('The evidence has been reviewed carefully.') }
  await page.getByRole('checkbox').check(); await page.getByRole('button', { name: dispute ? 'Review dispute action' : 'Review return action', exact: true }).click()
  await expect(page.getByLabel('Confirm reviewed action', { exact: true })).toBeFocused()
}
async function capture(page: Page, path: string) {
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path, fullPage: true })
}
for (const [status, target] of [['requested', 'approved'], ['approved', 'received'], ['received', 'received']] as const) test(`reviewed return ${status} action verifies saved state`, async ({ page }, info) => {
  const state = await setup(page, 'ready', status); await page.goto(`/admin/returns/${rid}`); await review(page)
  if (status === 'received') { await capture(page, info.outputPath('return-refund-review.png')); expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations).toEqual([]) }
  await page.getByRole('button', { name: 'Confirm return action', exact: true }).dblclick(); await expect(page.getByText('Action saved and confirmed in the latest records.', { exact: true })).toBeVisible()
  expect(state.writes).toHaveLength(1); expect(state.writes[0].body.expected_status).toBe(status); expect(state.writes[0].body.expected_notes).toBeNull()
  if (status === 'received') await expect(page.getByRole('link', { name: 'Inspect linked refund and transfer' })).toBeVisible()
  else await expect(page.getByText(new RegExp(target === 'approved' ? 'Approved ·' : 'Items received ·'))).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
test('reject action and notes are saved only after review', async ({ page }) => { const state = await setup(page); await page.goto(`/admin/returns/${rid}`); await page.getByLabel('Action', { exact: true }).selectOption('reject'); await page.getByLabel('Decision note (optional)').fill('Policy excludes this request'); await review(page); expect(state.writes).toHaveLength(0); await page.getByRole('button', { name: 'Back to draft' }).click(); await expect(page.getByRole('button', { name: 'Confirm return action' })).toHaveCount(0); await review(page); await page.getByRole('button', { name: 'Confirm return action' }).click(); await expect(page.getByText('Action saved and confirmed in the latest records.', { exact: true })).toBeVisible(); expect(state.writes[0].body.admin_note).toBe('Policy excludes this request') })
for (const kind of ['message', 'customer', 'seller']) test(`dispute ${kind} is reviewed and read back`, async ({ page }, info) => { const state = await setup(page); await page.goto(`/admin/disputes/${did}`); await review(page, true, kind); if (kind === 'customer') { await capture(page, info.outputPath('dispute-resolution-review.png')); expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations).toEqual([]) }; await page.getByRole('button', { name: 'Confirm dispute action' }).dblclick(); await expect(page.getByText('Action saved and confirmed in the latest records.', { exact: true })).toBeVisible(); expect(state.writes).toHaveLength(1); expect(state.writes[0].body.expected_message_count).toBe(1); expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true) })
for (const dispute of [false, true]) {
  test(`${dispute ? 'dispute' : 'return'} stale preflight sends nothing`, async ({ page }) => { const state = await setup(page); await page.goto(dispute ? `/admin/disputes/${did}` : `/admin/returns/${rid}`); await review(page, dispute); state.change(); await page.getByRole('button', { name: dispute ? 'Confirm dispute action' : 'Confirm return action' }).click(); await expect(page.getByRole('alert').first()).toContainText('changed'); expect(state.writes).toHaveLength(0) })
  for (const mode of ['lost', 'readback-denied', 'mismatch']) test(`${dispute ? 'dispute' : 'return'} ${mode} remains locked on reload`, async ({ page }) => { const state = await setup(page, mode); await page.goto(dispute ? `/admin/disputes/${did}` : `/admin/returns/${rid}`); await review(page, dispute); await page.getByRole('button', { name: dispute ? 'Confirm dispute action' : 'Confirm return action' }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); await page.reload(); await expect(page.getByText(/An action is awaiting confirmation/)).toBeVisible(); expect(state.writes).toHaveLength(1); const saved = await page.evaluate(() => JSON.stringify(sessionStorage)); expect(saved).not.toMatch(/fixture-token|carefully|customer@example/) })
  test(`${dispute ? 'dispute' : 'return'} known rejection permits correction without retry`, async ({ page }) => { const state = await setup(page, 'conflict'); await page.goto(dispute ? `/admin/disputes/${did}` : `/admin/returns/${rid}`); await review(page, dispute); await page.getByRole('button', { name: dispute ? 'Confirm dispute action' : 'Confirm return action' }).click(); await expect(page.getByRole('alert')).toContainText('Refresh and inspect'); await expect(page.getByRole('button', { name: 'Back to draft' })).toBeEnabled(); expect(state.writes).toHaveLength(1) })
}
test('queues filter and paginate without fabricating records', async ({ page }, info) => { await setup(page); await page.goto('/admin/returns'); await expect(page.getByText('Page 1 of 2 · 26 matching records')).toBeVisible(); await page.getByRole('button', { name: 'Next page' }).click(); await expect(page.getByText('Page 2 of 2 · 26 matching records')).toBeVisible(); await page.getByLabel('Status filter').selectOption('refunded'); await expect(page.getByText('No records on this page', { exact: true })).toBeVisible(); await page.goto('/admin/disputes'); await expect(page.getByRole('link', { name: `Review dispute ${did}`, exact: true })).toBeVisible(); await capture(page, info.outputPath('dispute-queue.png')) })
test('non-PKR refunds and resolved disputes are inspection-only', async ({ page }) => { const state = await setup(page, 'currency', 'received'); await page.goto(`/admin/returns/${rid}`); await expect(page.getByText(/No return action is currently available/)).toBeVisible(); expect(state.writes).toHaveLength(0) })
test('closed dispute does not offer a write form', async ({ page }) => { await setup(page, 'closed'); await page.goto(`/admin/disputes/${did}`); await expect(page.getByText(/This dispute is resolved or closed/)).toBeVisible(); await expect(page.getByRole('button', { name: 'Review dispute action' })).toHaveCount(0) })
for (const dispute of [false, true]) test(`malformed ${dispute ? 'dispute' : 'return'} detail cannot be acted on`, async ({ page }) => { await setup(page, 'malformed'); await page.goto(dispute ? `/admin/disputes/${did}` : `/admin/returns/${rid}`); await expect(page.getByRole('alert')).toBeVisible(); await expect(page.getByRole('checkbox')).toHaveCount(0) })
for (const [role, verified] of [['guest', true], ['customer', true], ['seller', true], ['admin', false]] as const) test(`${role} verified=${verified} cannot read private records`, async ({ page }) => { const state = await setup(page, 'ready', 'requested', role, verified); await page.goto(`/admin/returns/${rid}`); await expect(page.getByRole('heading', { level: 1 })).toHaveText(role === 'guest' ? 'Sign in to review returns' : !verified ? 'Verify your email first' : 'An administrator account is required'); expect(state.reads).toEqual([]); expect(state.writes).toEqual([]) })
