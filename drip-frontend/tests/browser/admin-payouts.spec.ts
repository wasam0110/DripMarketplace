import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111', owner = '22222222-2222-4222-8222-222222222222', seller = '33333333-3333-4333-8333-333333333333'
async function setup(page: Page, mode = 'ready', status = 'requested', role = 'admin', verified = true) {
  let value = { id, seller_id: seller, amount: '1500.25', payment_method: 'bank_transfer', payment_detail: 'Synthetic Bank — 00000001', status, admin_note: null as string | null, requested_at: '2026-11-05T00:00:00Z', completed_at: status === 'completed' ? '2026-11-05T01:00:00Z' : null, transfer_reference: status === 'completed' ? 'BANK-SAVED' : null, last_action_by: null as string | null, available_actions: status === 'requested' ? ['approve', 'reject'] : status === 'approved' ? ['reject', 'complete'] : status === 'processing' ? ['complete'] : [] }
  const writes: Record<string, unknown>[] = [], reads: string[] = []
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url()), path = url.pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: owner, role, email: 'admin@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (!path.includes('/admin/wallet/payouts')) return route.fulfill({ json: { data: [], total: 0 } })
    if (route.request().method() === 'GET') {
      reads.push(path)
      if (mode === 'denied' || mode === 'readback-denied' && writes.length) return route.fulfill({ status: 403, json: { error: { message: 'Record unavailable', code: 'FORBIDDEN' } } })
      if (path.endsWith('/payouts')) { const p = Number(url.searchParams.get('page')), empty = url.searchParams.get('status') !== value.status; return route.fulfill({ json: { data: empty ? [] : [{ ...value, id: p === 2 ? seller : id }], total: empty ? 0 : 26, page: p, total_pages: empty ? 1 : 2 } }) }
      return route.fulfill({ json: mode === 'malformed' ? { ...value, seller_id: 'invalid' } : value })
    }
    const body = route.request().postDataJSON(); writes.push(body)
    if (mode === 'lost') return route.abort('failed')
    if (mode === 'conflict') return route.fulfill({ status: 409, json: { error: { message: 'Refresh the changed payout', code: 'CONFLICT' } } })
    const action = path.split('/').pop(), next = action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'completed'
    value = { ...value, status: next, available_actions: next === 'approved' ? ['reject', 'complete'] : [], admin_note: body.admin_note ?? value.admin_note, last_action_by: owner, transfer_reference: action === 'complete' ? body.reference : null, completed_at: action === 'complete' ? '2026-11-05T01:00:00Z' : null }
    return route.fulfill({ json: mode === 'wrong-receipt' ? { ...value, amount: '1500.24' } : value })
  })
  return { writes, reads, change: () => { value.admin_note = 'Another administrator reviewed this payout' } }
}
async function review(page: Page, action = 'approve') {
  await page.getByLabel('Action', { exact: true }).selectOption(action)
  if (action === 'reject') await page.getByLabel('Rejection note').fill('Beneficiary must be verified')
  if (action === 'complete') await page.getByLabel('Transfer receipt reference').fill('BANK-001')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Review selected action' }).click()
}
for (const [status, action] of [['requested', 'approve'], ['requested', 'reject'], ['approved', 'complete'], ['processing', 'complete']]) test(`${status} ${action} checks receipt and prevents duplicate clicks`, async ({ page }, info) => {
  const state = await setup(page, 'ready', status); await page.goto(`/admin/payouts/${id}`); await review(page, action)
  if (status === 'approved') { await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('payout-transfer-review.png'), fullPage: true }); expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations).toEqual([]) }
  expect(state.writes).toHaveLength(0)
  await page.getByRole('button', { name: 'Confirm payout action' }).dblclick()
  await expect(page.getByText('Payout record verified. No transfer was initiated by this site.', { exact: true })).toBeVisible()
  expect(state.writes).toHaveLength(1); expect(state.writes[0].review).toMatchObject({ expected_status: status, expected_amount: '1500.25', expected_seller_id: seller })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
test('stale review sends no mutation', async ({ page }) => { const state = await setup(page); await page.goto(`/admin/payouts/${id}`); await review(page); state.change(); await page.getByRole('button', { name: 'Confirm payout action' }).click(); await expect(page.getByRole('alert').first()).toContainText('changed'); expect(state.writes).toHaveLength(0) })
for (const mode of ['lost', 'wrong-receipt', 'readback-denied']) test(`${mode} stays locked after reload without storing bank data`, async ({ page }) => { const state = await setup(page, mode); await page.goto(`/admin/payouts/${id}`); await review(page); await page.getByRole('button', { name: 'Confirm payout action' }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); await page.reload(); await expect(page.getByText(/A payout action is awaiting confirmation/)).toBeVisible(); expect(state.writes).toHaveLength(1); expect(await page.evaluate(() => JSON.stringify(sessionStorage))).not.toMatch(/Synthetic|00000001|fixture-token|1500/) })
test('known conflict permits fresh review without automatic retry', async ({ page }) => { const state = await setup(page, 'conflict'); await page.goto(`/admin/payouts/${id}`); await review(page); await page.getByRole('button', { name: 'Confirm payout action' }).click(); await expect(page.getByRole('alert').first()).toContainText('Refresh the changed payout'); await expect(page.getByRole('button', { name: 'Review selected action' })).toBeEnabled(); expect(state.writes).toHaveLength(1) })
test('queue filters and paginates without displaying bank destinations', async ({ page }) => { await setup(page); await page.goto('/admin/payouts'); await expect(page.getByText('Page 1 of 2 · 26 matching payouts')).toBeVisible(); await expect(page.getByText(/Synthetic Bank/)).toHaveCount(0); await page.getByRole('button', { name: 'Next payout page' }).click(); await expect(page.getByText('Page 2 of 2 · 26 matching payouts')).toBeVisible(); await page.getByLabel('Payout status').selectOption('completed'); await expect(page.getByText('No payouts on this page', { exact: true })).toBeVisible() })
for (const status of ['completed', 'rejected']) test(`${status} has no action form`, async ({ page }) => { await setup(page, 'ready', status); await page.goto(`/admin/payouts/${id}`); await expect(page.getByText(/No payout actions are available/)).toBeVisible(); await expect(page.getByRole('button', { name: 'Review selected action' })).toHaveCount(0) })
for (const [role, verified] of [['customer', true], ['seller', true], ['guest', true], ['admin', false]] as const) test(`${role} verified=${verified} cannot read payout data`, async ({ page }) => { const state = await setup(page, 'ready', 'requested', role, verified); await page.goto(`/admin/payouts/${id}`); await expect(page.getByRole('heading', { level: 1 })).toContainText(role === 'guest' ? 'Sign in' : !verified ? 'Verify your email' : 'administrator'); expect(state.reads).toHaveLength(0) })
for (const mode of ['malformed', 'denied']) test(`${mode} detail fails closed`, async ({ page }) => { await setup(page, mode); await page.goto(`/admin/payouts/${id}`); await expect(page.getByRole('alert').first()).toBeVisible(); await expect(page.getByRole('button', { name: 'Review selected action' })).toHaveCount(0) })
