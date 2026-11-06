import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111', other = '22222222-2222-4222-8222-222222222222'
async function setup(page: Page, mode = 'ready', role = 'admin', verified = true) {
  const writes: { method: string; body: unknown; query: string }[] = [], reads: string[] = []
  let denied = mode === 'denied', row = { id, title: 'Linen season', image_url: 'https://images.example.test/banner.svg', link_url: '/clothing' as string | null, position: 'homepage_hero', sort_order: 0, is_active: false, valid_from: null as string | null, valid_until: null as string | null, created_at: '2026-10-28T00:00:00Z', updated_at: '2026-10-28T00:00:00Z' }, exists = !['empty', 'create', 'lost-create'].includes(mode)
  await page.route('https://images.example.test/**', (route) => route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="240"><rect width="600" height="240" fill="#d6d0c3"/><text x="300" y="120" text-anchor="middle" fill="#203c32">Test banner artwork</text></svg>' }))
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'admin-owner', role, email: 'admin@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (!path.includes('/admin/content/banners')) return route.fulfill({ status: 404, json: {} })
    expect(route.request().headers().authorization).toBe('Bearer fixture-token')
    if (method !== 'GET') {
      const body = method === 'PATCH' ? route.request().postDataJSON() : route.request().postData(); writes.push({ method, body, query: url.search })
      if (mode === 'rejection' || mode === 'conflict') return route.fulfill({ status: mode === 'conflict' ? 409 : 422, json: { error: { message: 'Inspect the current banner before changing it.' } } })
      if (method === 'PATCH') { const { expected_updated_at: _version, ...changes } = body; row = { ...row, ...changes, updated_at: '2026-10-28T01:00:00Z' } }
      if (method === 'POST') { row = { ...row, id: other, title: 'New season', link_url: null, position: 'homepage_secondary', sort_order: 2, updated_at: '2026-10-28T01:00:00Z' }; exists = true }
      if (method === 'DELETE') exists = false
      if (mode === 'lost' || mode === 'lost-create') return route.abort()
      return method === 'DELETE' ? route.fulfill({ status: 204 }) : route.fulfill({ status: method === 'POST' ? 201 : 200, json: { ...row, ...(mode === 'wrong-receipt' ? { id: other } : {}) } })
    }
    reads.push(`${path}${url.search}`)
    if (denied || (mode === 'readback-denied' && writes.length)) return route.fulfill({ status: 403, json: { error: { message: 'Banner list unavailable' } } })
    return route.fulfill({ json: exists ? [{ ...row, ...(mode === 'missing-version' ? { updated_at: undefined } : {}), ...(mode === 'readback-mismatch' && writes.length ? { title: 'Different saved title' } : {}) }] : mode === 'delete-mismatch' && writes.length ? [row] : [] })
  })
  return { writes, reads, change: () => { row = { ...row, title: 'Updated by another admin', updated_at: '2026-10-28T00:30:00Z' } }, allow: () => { denied = false } }
}
const open = (page: Page) => page.goto(`/admin/content/banners/${id}`)
async function edit(page: Page) { await page.getByLabel('Banner title', { exact: true }).fill('Autumn linen'); await page.getByRole('button', { name: 'Review banner changes', exact: true }).click() }
async function image(page: Page) {
  const base64 = await page.evaluate(() => { const canvas = document.createElement('canvas'); canvas.width = 24; canvas.height = 24; canvas.getContext('2d')!.fillRect(0, 0, 24, 24); return canvas.toDataURL('image/png').split(',')[1] })
  return { name: 'test-banner.png', mimeType: 'image/png', buffer: Buffer.from(base64, 'base64') }
}
test('list and edit review are accessible and fit the viewport', async ({ page }, info) => {
  const state = await setup(page); await page.goto('/admin/content'); await expect(page.getByRole('link', { name: 'Manage Linen season' })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]); expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.screenshot({ path: info.outputPath('admin-banner-list.png'), fullPage: true })
  await page.getByRole('link', { name: 'Manage Linen season' }).click(); await edit(page); expect(state.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]); expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('admin-banner-review.png'), fullPage: true })
})
test('edit is one versioned write confirmed by list readback', async ({ page }) => {
  const state = await setup(page); await open(page); await edit(page); await page.getByRole('button', { name: 'Confirm banner changes', exact: true }).dblclick(); await expect(page.getByText('Banner saved and confirmed.', { exact: true })).toBeVisible()
  expect(state.writes).toHaveLength(1); expect(state.writes[0].body).toMatchObject({ title: 'Autumn linen', expected_updated_at: '2026-10-28T00:00:00Z' }); await expect(page.getByRole('heading', { name: 'Autumn linen', exact: true })).toBeVisible()
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toMatch(/fixture-token|Autumn linen/)
})
test('creation previews locally, defaults inactive and verifies multipart receipt', async ({ page }, info) => {
  const state = await setup(page, 'create'); await page.goto('/admin/content/banners/new'); await page.getByLabel('Banner title', { exact: true }).fill('New season'); await page.getByLabel('Placement', { exact: true }).selectOption('homepage_secondary'); await page.getByLabel('Sort order', { exact: true }).fill('2'); await page.getByLabel('Banner image', { exact: true }).setInputFiles(await image(page)); await expect(page.getByAltText('Selected banner preview, not yet uploaded')).toBeVisible(); await expect(page.getByLabel('Banner is active', { exact: true })).not.toBeChecked(); expect(state.writes).toEqual([])
  await page.getByRole('button', { name: 'Review banner changes', exact: true }).click(); await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('admin-banner-create.png'), fullPage: true }); await page.getByRole('button', { name: 'Confirm banner changes', exact: true }).dblclick(); await expect(page.getByRole('link', { name: 'Open the created banner' })).toHaveAttribute('href', `/admin/content/banners/${other}`)
  expect(state.writes).toHaveLength(1); expect(state.writes[0].method).toBe('POST'); expect(state.writes[0].body).toContain('name="image"'); expect(state.writes[0].body).toContain('name="is_active"\r\n\r\nfalse')
})
test('UTC schedules can be set and cleared with the active flag', async ({ page }) => {
  const state = await setup(page); await open(page); await page.getByLabel('Starts (UTC, optional)', { exact: true }).fill('2026-10-29T10:00'); await page.getByLabel('Ends (UTC, optional)', { exact: true }).fill('2026-10-30T10:00'); await page.getByLabel('Banner is active', { exact: true }).check(); await page.getByRole('button', { name: 'Review banner changes', exact: true }).click(); await page.getByRole('button', { name: 'Confirm banner changes', exact: true }).click(); await expect(page.getByText('Banner saved and confirmed.', { exact: true })).toBeVisible(); expect(state.writes[0].body).toMatchObject({ valid_from: '2026-10-29T10:00:00.000Z', valid_until: '2026-10-30T10:00:00.000Z', is_active: true })
  await page.getByLabel('Starts (UTC, optional)', { exact: true }).fill(''); await page.getByLabel('Ends (UTC, optional)', { exact: true }).fill(''); await page.getByLabel('Destination link (optional)', { exact: true }).fill(''); await page.getByRole('button', { name: 'Review banner changes', exact: true }).click(); await page.getByRole('button', { name: 'Confirm banner changes', exact: true }).click(); await expect.poll(() => state.writes.length).toBe(2); expect(state.writes[1].body).toMatchObject({ valid_from: null, valid_until: null, link_url: null })
})
test('uncertain creation locks new uploads after a same-tab reload', async ({ page }) => {
  const state = await setup(page, 'lost-create'); await page.goto('/admin/content/banners/new'); await page.getByLabel('Banner title', { exact: true }).fill('New season'); await page.getByLabel('Banner image', { exact: true }).setInputFiles(await image(page)); await page.getByRole('button', { name: 'Review banner changes', exact: true }).click(); await page.getByRole('button', { name: 'Confirm banner changes', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); await page.reload(); await expect(page.getByText(/A banner change is awaiting confirmation/)).toBeVisible(); await expect(page.getByLabel('Banner image', { exact: true })).toBeDisabled(); expect(state.writes).toHaveLength(1)
})
test('deletion can be cancelled and confirmed once with the reviewed version', async ({ page }) => {
  const state = await setup(page); await open(page); await page.getByRole('button', { name: 'Review deleting banner', exact: true }).click(); await page.getByRole('button', { name: 'Keep banner', exact: true }).click(); expect(state.writes).toEqual([]); await page.getByRole('button', { name: 'Review deleting banner', exact: true }).click(); await page.getByRole('button', { name: 'Confirm banner deletion', exact: true }).dblclick(); await expect(page.getByText('Banner record deleted and confirmed.', { exact: true })).toBeVisible(); expect(state.writes).toHaveLength(1); expect(state.writes[0].method).toBe('DELETE'); expect(new URLSearchParams(state.writes[0].query).get('expected_updated_at')).toBe('2026-10-28T00:00:00Z')
})
test('changed preflight content never writes', async ({ page }) => {
  const state = await setup(page); await open(page); await edit(page); state.change(); await page.getByRole('button', { name: 'Confirm banner changes', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('changed or was removed'); expect(state.writes).toEqual([])
})
for (const mode of ['lost', 'wrong-receipt', 'readback-mismatch', 'readback-denied']) test(`${mode} locks updates across reload`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await edit(page); await page.getByRole('button', { name: 'Confirm banner changes', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); await page.reload(); await expect(page.getByText(/A banner change is awaiting confirmation/)).toBeVisible(); await page.getByRole('button', { name: 'Refresh banners and discard review', exact: true }).click(); await expect(page.getByText(/A banner change is awaiting confirmation/)).toBeVisible(); expect(state.writes).toHaveLength(1)
})
test('missing deletion readback locks further changes', async ({ page }) => {
  const state = await setup(page, 'delete-mismatch'); await open(page); await page.getByRole('button', { name: 'Review deleting banner', exact: true }).click(); await page.getByRole('button', { name: 'Confirm banner deletion', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['rejection', 'conflict']) test(`${mode} permits correction but never replays a write`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await edit(page); await page.getByRole('button', { name: 'Confirm banner changes', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('Inspect the current banner'); await expect(page.getByRole('button', { name: 'Back to banner form', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
test('invalid links, dates and no-op updates never send writes', async ({ page }) => {
  const state = await setup(page); await open(page); await page.getByRole('button', { name: 'Review banner changes', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('Change a banner field'); await page.getByLabel('Destination link (optional)', { exact: true }).fill('/\\example.test'); await page.getByRole('button', { name: 'Review banner changes', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('HTTPS'); await page.getByLabel('Destination link (optional)', { exact: true }).fill('/clothing'); await page.getByLabel('Starts (UTC, optional)', { exact: true }).fill('2026-10-30T10:00'); await page.getByLabel('Ends (UTC, optional)', { exact: true }).fill('2026-10-29T10:00'); await page.getByRole('button', { name: 'Review banner changes', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('end must follow'); expect(state.writes).toEqual([])
})
test('SVG and oversized image selections stay local and are rejected', async ({ page }) => {
  const state = await setup(page, 'create'); await page.goto('/admin/content/banners/new'); await page.getByLabel('Banner image', { exact: true }).setInputFiles({ name: 'bad.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg/>') }); await expect(page.getByRole('alert')).toContainText('JPEG, PNG or WebP'); await page.getByLabel('Banner image', { exact: true }).setInputFiles({ name: 'large.png', mimeType: 'image/png', buffer: Buffer.alloc(5 * 1024 * 1024 + 1) }); await expect(page.getByRole('alert')).toContainText('5 MiB'); expect(state.writes).toEqual([])
})
test('empty lists and missing banners do not fabricate content', async ({ page }) => {
  const state = await setup(page, 'empty'); await page.goto('/admin/content'); await expect(page.getByText('No banners yet', { exact: true })).toBeVisible(); await open(page); await expect(page.getByText('This banner is no longer in the saved list.', { exact: true })).toBeVisible(); expect(state.writes).toEqual([])
})
test('denied list reads are retryable', async ({ page }) => {
  const state = await setup(page, 'denied'); await page.goto('/admin/content'); await expect(page.getByRole('alert')).toContainText('unavailable'); state.allow(); await page.getByRole('button', { name: 'Refresh banners and discard review', exact: true }).click(); await expect(page.getByRole('link', { name: 'Manage Linen season' })).toBeVisible(); expect(state.writes).toEqual([])
})
test('missing version blocks all saved-banner actions', async ({ page }) => { await setup(page, 'missing-version'); await open(page); await expect(page.getByRole('alert')).toContainText('could not be verified'); await expect(page.getByRole('button', { name: 'Review banner changes', exact: true })).toHaveCount(0) })
test('invalid reference sends no content reads', async ({ page }) => { const state = await setup(page); await page.goto('/admin/content/banners/invalid'); await expect(page.getByRole('alert')).toContainText('invalid'); expect(state.reads).toEqual([]) })
for (const [role, verified, heading] of [['guest', true, 'Sign in to manage banners'], ['customer', true, 'An administrator account is required'], ['seller', true, 'An administrator account is required'], ['Admin', true, 'An administrator account is required'], ['admin', false, 'Verify your email first']] as const) test(`${role} verified=${verified} cannot access content APIs`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await page.goto('/admin/content'); await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading); expect(state.reads).toEqual([]); expect(state.writes).toEqual([])
})
