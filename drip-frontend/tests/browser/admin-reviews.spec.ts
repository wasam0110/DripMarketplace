import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111', product = '22222222-2222-4222-8222-222222222222', other = '33333333-3333-4333-8333-333333333333'
async function setup(page: Page, mode = 'ready', role = 'admin', verified = true) {
  let status = ['approved', 'rejected', 'hidden'].includes(mode) ? mode : 'pending', note: string | null = mode === 'approved' ? 'Existing private note' : null
  let updated = '2026-10-28T00:00:00Z', moderated: string | null = null, body = '<script>window.reviewExecuted=true</script>Soft linen.', votes = 0, denied = mode === 'denied'
  const writes: unknown[] = [], reads: string[] = []
  const detail = () => ({ id, product_id: product, user: { id: other, first_name: 'Ayesha', last_name: 'Khan', avatar_url: null }, rating: 4, title: 'Beautiful linen', body, status, is_verified_purchase: true, helpful_count: votes, unhelpful_count: 0, images: mode === 'photos' ? [{ id: other, url: 'https://images.example.test/review.svg', sort_order: 0 }] : [], admin_note: note, moderated_at: moderated, updated_at: updated, created_at: '2026-10-27T00:00:00Z' })
  await page.route('https://images.example.test/**', (route) => route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="280"><rect width="240" height="280" fill="#d6d0c3"/><text x="120" y="140" text-anchor="middle" fill="#203c32">Test review photo</text></svg>' }))
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'admin-owner', role, email: 'admin@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (!path.includes('/admin/reviews')) return route.fulfill({ status: 404, json: {} })
    expect(route.request().headers().authorization).toBe('Bearer fixture-token')
    if (method === 'PATCH') {
      const payload = route.request().postDataJSON(); writes.push(payload)
      if (mode === 'rejection' || mode === 'conflict') return route.fulfill({ status: mode === 'conflict' ? 409 : 422, json: { error: { message: 'Refresh and inspect the review.' } } })
      status = payload.status; note = payload.admin_note; updated = '2026-10-28T01:00:00Z'; moderated = updated
      if (mode === 'lost') return route.abort()
      return route.fulfill({ json: { ...detail(), ...(mode === 'wrong-receipt' ? { id: other } : {}) } })
    }
    reads.push(`${path}${url.search}`)
    if (denied || (mode === 'readback-denied' && writes.length)) return route.fulfill({ status: 403, json: { error: { message: 'Review detail unavailable' } } })
    if (path.endsWith('/admin/reviews')) {
      const pageNumber = Number(url.searchParams.get('page') || 1), filter = url.searchParams.get('status')
      if (mode === 'slow' && filter === 'hidden') await new Promise((resolve) => setTimeout(resolve, 500))
      return route.fulfill({ json: { data: mode === 'empty' ? [] : [{ ...detail(), id: pageNumber === 1 ? id : other, status: filter || status, title: mode === 'slow' && filter === 'hidden' ? 'Stale hidden review' : 'Beautiful linen' }], page: pageNumber, per_page: 25, total: mode === 'empty' ? 0 : 26 } })
    }
    return route.fulfill({ json: { ...detail(), ...(mode === 'wrong-id' ? { id: other } : {}), ...(mode === 'missing-note' ? { admin_note: undefined } : {}), ...(mode === 'readback-mismatch' && writes.length ? { admin_note: 'Different note' } : {}) } })
  })
  return { writes, reads, allow: () => { denied = false }, change: (kind: string) => { if (kind === 'body') { body = 'Changed review content.'; updated = '2026-10-28T00:30:00Z' }; if (kind === 'votes') votes = 3 } }
}
const open = (page: Page) => page.goto(`/admin/reviews/${id}`)
async function review(page: Page, status = 'approved', note = 'Checked eligibility') {
  await page.getByLabel('Decision', { exact: true }).selectOption(status); await page.getByLabel('Private admin note (optional)', { exact: true }).fill(note); await page.getByRole('button', { name: 'Review moderation decision', exact: true }).click()
}
test('filtered lists reset pages and expose only supported query fields', async ({ page }, info) => {
  const state = await setup(page); await page.goto('/admin/reviews'); await expect(page.getByRole('heading', { name: 'Beautiful linen' })).toBeVisible()
  expect(state.reads).toContain('/api/v1/admin/reviews?page=1&status=pending')
  await page.getByRole('button', { name: 'Next review page', exact: true }).click(); await expect(page.getByText('Page 2 of 2 · 26 reviews', { exact: true })).toBeVisible()
  await page.getByLabel('Review status', { exact: true }).selectOption('all'); await expect(page.getByText('Page 1 of 2 · 26 reviews', { exact: true })).toBeVisible(); expect(state.reads).toContain('/api/v1/admin/reviews?page=1')
  await page.reload(); await expect(page.getByLabel('Review status', { exact: true })).toHaveValue('all'); await expect(page.getByText('Page 1 of 2 · 26 reviews', { exact: true })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('admin-review-list.png'), fullPage: true }); expect(state.writes).toEqual([])
})
test('reviewed approval is one versioned write followed by private readback', async ({ page }, info) => {
  const state = await setup(page, 'photos'); await open(page); await expect(page.getByRole('link', { name: 'Inspect reviewed product' })).toHaveAttribute('href', `/admin/products/${product}`)
  await expect(page.getByText('<script>window.reviewExecuted=true</script>Soft linen.', { exact: true })).toBeVisible(); expect(await page.evaluate(() => 'reviewExecuted' in window)).toBe(false)
  await review(page); expect(state.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('admin-review-decision.png'), fullPage: true })
  await page.getByRole('button', { name: 'Confirm review moderation', exact: true }).dblclick(); await expect(page.getByText('Review moderation saved and confirmed.', { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ status: 'approved', admin_note: 'Checked eligibility', expected_updated_at: '2026-10-28T00:00:00Z' }])
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toMatch(/fixture-token|Checked eligibility|Beautiful linen/)
})
for (const status of ['hidden', 'rejected']) test(`${status} decision preserves review content`, async ({ page }) => {
  const state = await setup(page); await open(page); await review(page, status); await page.getByRole('button', { name: 'Confirm review moderation', exact: true }).click(); await expect(page.getByText('Review moderation saved and confirmed.', { exact: true })).toBeVisible(); expect(state.writes).toHaveLength(1); await expect(page.getByText('<script>window.reviewExecuted=true</script>Soft linen.', { exact: true })).toBeVisible()
})
test('existing note can be explicitly cleared while hiding an approved review', async ({ page }) => {
  const state = await setup(page, 'approved'); await open(page); await review(page, 'hidden', '  '); await page.getByRole('button', { name: 'Confirm review moderation', exact: true }).click(); await expect(page.getByText('Review moderation saved and confirmed.', { exact: true })).toBeVisible(); expect(state.writes[0]).toMatchObject({ admin_note: null, status: 'hidden' })
})
test('changed content is refreshed before any write', async ({ page }) => {
  const state = await setup(page); await open(page); await review(page); state.change('body'); await page.getByRole('button', { name: 'Confirm review moderation', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('changed'); expect(state.writes).toEqual([])
})
test('vote count changes do not block a reviewed decision', async ({ page }) => {
  const state = await setup(page); await open(page); await review(page); state.change('votes'); await page.getByRole('button', { name: 'Confirm review moderation', exact: true }).click(); await expect(page.getByText('Review moderation saved and confirmed.', { exact: true })).toBeVisible(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['lost', 'wrong-receipt', 'readback-mismatch', 'readback-denied']) test(`${mode} locks writes across reload and refresh`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm review moderation', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); await page.reload(); await expect(page.getByText(/A review decision is awaiting confirmation/)).toBeVisible(); await page.getByRole('button', { name: 'Refresh review and discard decision', exact: true }).click(); await expect(page.getByText(/A review decision is awaiting confirmation/)).toBeVisible(); const button = page.getByRole('button', { name: 'Review moderation decision', exact: true }); if (await button.count()) await expect(button).toBeDisabled(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['rejection', 'conflict']) test(`${mode} is not retried automatically`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page); await page.getByRole('button', { name: 'Back to decision', exact: true }).click(); expect(state.writes).toEqual([]); await review(page); await page.getByRole('button', { name: 'Confirm review moderation', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('Refresh and inspect'); await expect(page.getByRole('button', { name: 'Back to decision', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['wrong-id', 'missing-note']) test(`${mode} blocks actions`, async ({ page }) => {
  await setup(page, mode); await open(page); await expect(page.getByRole('alert')).toContainText('could not be verified'); await expect(page.getByRole('button', { name: 'Review moderation decision', exact: true })).toHaveCount(0)
})
test('empty list is explicit', async ({ page }) => {
  const state = await setup(page, 'empty'); await page.goto('/admin/reviews'); await expect(page.getByText('No reviews on this page', { exact: true })).toBeVisible(); await expect(page.getByRole('button', { name: 'Next review page', exact: true })).toBeDisabled(); expect(state.writes).toEqual([])
})
test('denied reads have an explicit retry', async ({ page }) => {
  const state = await setup(page, 'denied'); await open(page); await expect(page.getByRole('alert')).toContainText('unavailable'); state.allow(); await page.getByRole('button', { name: 'Refresh review and discard decision', exact: true }).click(); await expect(page.getByRole('button', { name: 'Review moderation decision', exact: true })).toBeEnabled(); expect(state.writes).toEqual([])
})
test('stale list responses do not replace a current status filter', async ({ page }) => {
  await setup(page, 'slow'); await page.goto('/admin/reviews'); await page.getByLabel('Review status', { exact: true }).selectOption('hidden'); await page.getByLabel('Review status', { exact: true }).selectOption('approved'); await expect(page.getByRole('heading', { name: 'Beautiful linen' })).toBeVisible(); await page.waitForTimeout(650); await expect(page.getByText('Stale hidden review', { exact: true })).toHaveCount(0)
})
for (const path of ['/admin/reviews/invalid', '/admin/reviews?status=unknown', '/admin/reviews?page=0']) test(`${path} sends no admin reads`, async ({ page }) => {
  const state = await setup(page); await page.goto(path); await expect(page.getByRole('alert')).toBeVisible(); expect(state.reads).toEqual([])
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to moderate reviews'], ['customer', true, 'An administrator account is required'], ['seller', true, 'An administrator account is required'], ['Admin', true, 'An administrator account is required'], ['admin', false, 'Verify your email first']] as const) test(`${role} verified=${verified} cannot read or moderate`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading); expect(state.reads).toEqual([]); expect(state.writes).toEqual([])
})
