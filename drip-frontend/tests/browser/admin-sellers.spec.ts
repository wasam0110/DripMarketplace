import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const sellerId = '11111111-1111-4111-8111-111111111111', otherId = '22222222-2222-4222-8222-222222222222'
const reason = 'Please provide a complete return policy.'
async function setup(page: Page, mode = 'ready', role = 'admin', verified = true) {
  let status = ({ active: 'active', suspended: 'suspended', rejected: 'rejected', payment: 'pending_payment', unknown: 'future_state' } as Record<string, string>)[mode] || 'pending_approval'
  let savedReason: string | null = mode === 'suspended' ? 'Previously suspended for policy review.' : null, policy = 'Returns within seven days.'
  let denied = mode === 'denied'
  const reads: string[] = [], writes: { path: string; body: unknown }[] = []
  const detail = () => ({ id: sellerId, brand_name: 'Fixture Label', status, slots_used: 1, total_slots: 5, product_count: 1, total_gmv: '1000.25', platform_cut: '150.03', available_balance: '500.25', joined_at: '2026-10-28T10:00:00Z', slug: 'fixture-label', description: 'Independent everyday clothing.', whatsapp_number: '+923001234567', instagram_handle: '@fixturelabel', logo_url: null, return_policy: policy, pending_balance: '200.00', registration_fee: mode === 'payment' ? '5000.00' : '0.00', rejected_reason: savedReason, registration_amount_due: mode === 'payment' && status === 'pending_payment' ? '5000.00' : '0.00', registration_paid_at: null, registration_payment_reference: null, registration_paid_by: null })
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'admin-owner', role, email: 'admin@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.includes('/admin/')) {
      expect(route.request().headers().authorization).toBe('Bearer fixture-token')
      if (method === 'GET') reads.push(`${path}${url.search}`)
      else {
        const body = route.request().postData() ? route.request().postDataJSON() : null; writes.push({ path, body })
        if (mode === 'known-rejection') return route.fulfill({ status: 400, json: { error: { message: 'Seller decision is no longer eligible.' } } })
        const action = path.split('/').at(-1)
        status = action === 'approve' || action === 'reinstate' ? 'active' : action === 'reject' ? 'rejected' : 'suspended'; if (body?.reason) savedReason = body.reason
        if (mode === 'lost') return route.abort()
        return route.fulfill({ json: { message: 'Saved' } })
      }
      if (denied || (mode === 'readback-denied' && writes.length)) return route.fulfill({ status: 403, json: { error: { message: 'Seller records unavailable' } } })
      if (path.endsWith('/admin/sellers')) {
        const p = Number(url.searchParams.get('page') || 1), filter = url.searchParams.get('status') || 'all'
        if (mode === 'slow-list' && filter === 'active') await new Promise((resolve) => setTimeout(resolve, 500))
        const row = { ...detail(), id: p === 2 ? otherId : sellerId, brand_name: mode === 'slow-list' && filter === 'active' ? 'Old active result' : 'Fixture Label', status: filter === 'all' ? status : filter }
        return route.fulfill({ json: { data: mode === 'empty' ? [] : [row], total: mode === 'empty' ? 0 : 26, page: p, per_page: 25, total_pages: mode === 'empty' ? 1 : 2 } })
      }
      if (path.endsWith(`/sellers/${sellerId}`)) {
        return route.fulfill({ json: { ...detail(), ...(mode === 'wrong-id' ? { id: otherId } : {}), ...(mode === 'malformed' ? { pending_balance: 200 } : {}), ...(mode === 'mismatch' && writes.length ? { status: 'pending_approval' } : {}) } })
      }
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return { reads, writes, allow: () => { denied = false }, changeReviewedRecord: () => { if (mode === 'changed-status') status = 'rejected'; if (mode === 'changed-policy') policy = 'A new policy requiring another review.' } }
}
const open = (page: Page) => page.goto(`/admin/sellers/${sellerId}`)
async function review(page: Page, action = 'approve') {
  await page.getByLabel('Review action', { exact: true }).selectOption(action)
  if (action === 'reject' || action === 'suspend') await page.getByLabel('Decision reason', { exact: true }).fill(reason)
  await page.getByRole('button', { name: 'Review seller decision', exact: true }).click()
}
test('seller list supports status/search filters and resets pagination', async ({ page }, info) => {
  const state = await setup(page); await page.goto('/admin/sellers'); await expect(page.getByRole('link', { name: 'Review Fixture Label' })).toHaveAttribute('href', `/admin/sellers/${sellerId}`)
  await page.getByRole('button', { name: 'Next seller page', exact: true }).click(); await expect(page.getByText('Page 2 of 2 · 26 matching sellers', { exact: true })).toBeVisible()
  await page.getByLabel('Seller status', { exact: true }).selectOption('active'); await expect(page.getByText('Page 1 of 2 · 26 matching sellers', { exact: true })).toBeVisible()
  await page.getByLabel('Search brand name', { exact: true }).fill('Linen & Co'); await page.getByRole('button', { name: 'Search sellers', exact: true }).click()
  await expect.poll(() => state.reads.some((value) => value.includes('q=Linen+%26+Co'))).toBe(true)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('admin-seller-list.png'), fullPage: true })
  expect(state.writes).toEqual([])
})
test('approval requires review, explicit confirmation and matching readback', async ({ page }, info) => {
  const state = await setup(page); await open(page); await review(page)
  expect(state.writes).toEqual([]); await expect(page.getByText('Quoted registration fee', { exact: true })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('admin-seller-review.png'), fullPage: true })
  await page.getByRole('button', { name: 'Confirm seller decision', exact: true }).dblclick(); await expect(page.getByText('Seller decision saved and confirmed.', { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ path: `/api/v1/admin/sellers/${sellerId}/approve`, body: null }]); await expect(page.getByLabel('Review action', { exact: true })).toHaveValue('suspend')
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain('fixture-token')
})
for (const [mode, action, result] of [['ready', 'reject', 'Rejected'], ['active', 'suspend', 'Suspended'], ['suspended', 'reinstate', 'Active']] as const) test(`${action} confirms the saved state and reason`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page, action); await page.getByRole('button', { name: 'Confirm seller decision', exact: true }).click()
  await expect(page.getByText('Seller decision saved and confirmed.', { exact: true })).toBeVisible(); await expect(page.getByText(result, { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ path: `/api/v1/admin/sellers/${sellerId}/${action}`, body: action === 'reinstate' ? null : { reason } }])
  if (action !== 'reinstate') await expect(page.getByText(reason, { exact: true })).toBeVisible()
})
test('too-short reason and backing out do not submit', async ({ page }) => {
  const state = await setup(page); await open(page); await page.getByLabel('Review action', { exact: true }).selectOption('reject'); await page.getByLabel('Decision reason', { exact: true }).fill('short')
  await page.getByRole('button', { name: 'Review seller decision', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('10 and 1,000')
  await review(page, 'reject'); await page.getByRole('button', { name: 'Back to decision edits', exact: true }).click(); expect(state.writes).toEqual([])
})
for (const mode of ['changed-status', 'changed-policy']) test(`preflight catches ${mode} without sending a decision`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page); state.changeReviewedRecord(); await page.getByRole('button', { name: 'Confirm seller decision', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('changed'); expect(state.writes).toEqual([])
})
for (const mode of ['lost', 'mismatch', 'readback-denied']) test(`${mode} decision stays locked across reload`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm seller decision', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await expect(page.getByText('Seller decision saved and confirmed.', { exact: true })).toHaveCount(0)
  await page.reload(); await expect(page.getByText(/A seller update is awaiting confirmation/)).toBeVisible(); expect(state.writes).toHaveLength(1)
  const button = page.getByRole('button', { name: 'Review seller decision', exact: true }); if (await button.count()) await expect(button).toBeDisabled()
})
test('known rejection allows editing but never replays a write', async ({ page }) => {
  const state = await setup(page, 'known-rejection'); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm seller decision', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('no longer eligible')
  await expect(page.getByRole('button', { name: 'Back to decision edits', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
test('registration-payment pending never offers approval or records money', async ({ page }) => {
  const state = await setup(page, 'payment'); await open(page); await expect(page.getByLabel('Review action', { exact: true })).toHaveValue('reject')
  await expect(page.getByRole('option', { name: 'Approve seller', exact: true })).toHaveCount(0); await expect(page.getByText(/Approval is unavailable while registration payment is pending/)).toBeVisible(); expect(state.writes).toEqual([])
})
for (const mode of ['rejected', 'unknown']) test(`${mode} state is read-only`, async ({ page }) => {
  await setup(page, mode); await open(page); await expect(page.getByText('No review action is available for this seller status.', { exact: true })).toBeVisible(); await expect(page.getByRole('button', { name: 'Review seller decision', exact: true })).toHaveCount(0)
})
for (const mode of ['wrong-id', 'malformed']) test(`${mode} detail cannot enable decisions`, async ({ page }) => {
  await setup(page, mode); await open(page); await expect(page.getByRole('alert')).toContainText('could not be verified'); await expect(page.getByRole('button', { name: 'Review seller decision', exact: true })).toHaveCount(0)
})
test('denied list reads can be retried and empty pages stay empty', async ({ page }) => {
  const state = await setup(page, 'denied'); await page.goto('/admin/sellers'); await expect(page.getByRole('alert')).toContainText('Seller records unavailable'); state.allow(); await page.getByRole('button', { name: 'Refresh seller list', exact: true }).click(); await expect(page.getByRole('link', { name: 'Review Fixture Label' })).toBeVisible()
})
test('empty application list displays no fabricated sellers', async ({ page }) => {
  await setup(page, 'empty'); await page.goto('/admin/sellers'); await expect(page.getByText('No sellers on this page', { exact: true })).toBeVisible(); await expect(page.getByRole('button', { name: 'Next seller page', exact: true })).toBeDisabled()
})
test('late responses from an old status filter do not replace the selected list', async ({ page }) => {
  await setup(page, 'slow-list'); await page.goto('/admin/sellers'); await page.getByLabel('Seller status', { exact: true }).selectOption('active'); await page.getByLabel('Seller status', { exact: true }).selectOption('rejected')
  await expect(page.getByRole('link', { name: 'Review Fixture Label' })).toBeVisible(); await page.waitForTimeout(650); await expect(page.getByText('Old active result', { exact: true })).toHaveCount(0)
})
test('invalid seller references do not reach the admin API', async ({ page }) => {
  const state = await setup(page); await page.goto('/admin/sellers/not-an-id'); await expect(page.getByRole('alert')).toHaveText('This seller reference is invalid.'); expect(state.reads).toEqual([])
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to review sellers'], ['customer', true, 'An administrator account is required'], ['seller', true, 'An administrator account is required'], ['Admin', true, 'An administrator account is required'], ['admin', false, 'Verify your email first']] as const) test(`${role} verified=${verified} cannot read admin seller data`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading); expect(state.reads).toEqual([]); expect(state.writes).toEqual([])
})
