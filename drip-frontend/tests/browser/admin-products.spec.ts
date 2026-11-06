import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111', seller = '22222222-2222-4222-8222-222222222222', other = '33333333-3333-4333-8333-333333333333'
async function setup(page: Page, mode = 'ready', role = 'admin', verified = true) {
  let hidden = ['hidden', 'draft', 'suspended', 'archived'].includes(mode), price = '1500.25', sellerStatus = mode === 'suspended' ? 'suspended' : 'active', stock = 8
  const published = mode !== 'draft', writes: string[] = [], reads: string[] = []
  let description = 'An everyday linen coat.', denied = mode === 'denied'
  const detail = () => ({ id, seller_id: seller, name: 'Linen coat', slug: 'linen-coat', price, sale_price: '1200.75', description, meta_title: 'Linen coat', meta_description: null, is_published: published, admin_hidden: hidden, seller_status: sellerStatus, seller_deleted: mode === 'archived', seller: { id: seller, brand_name: 'Fixture Label', return_policy: 'Seven-day returns.' }, category: null, created_at: '2026-10-28T10:00:00Z', images: mode === 'empty-detail' ? [] : [{ id: other, url: 'https://images.example.test/coat.svg', alt_text: 'Test coat image', sort_order: 0, is_primary: true }], variants: mode === 'empty-detail' ? [] : [{ id: other, sku: 'WHZ-COAT', size_type: 'alpha', size_value: 'M', colour: 'Ivory', price: '1200.75', stock, available_stock: stock - 2, is_active: true }] })
  await page.route('https://images.example.test/**', (route) => route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="280"><rect width="240" height="280" fill="#d6d0c3"/><text x="120" y="140" text-anchor="middle" fill="#203c32">Test image</text></svg>' }))
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'admin-owner', role, email: 'admin@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.includes('/admin/products')) {
      expect(route.request().headers().authorization).toBe('Bearer fixture-token')
      if (method === 'POST') {
        writes.push(path)
        if (mode === 'rejection') return route.fulfill({ status: 422, json: { error: { message: 'Product cannot be changed now.' } } })
        hidden = path.endsWith('/hide')
        if (mode === 'lost') return route.abort()
        return route.fulfill({ json: { id: mode === 'wrong-receipt' ? other : id, admin_hidden: hidden } })
      }
      reads.push(`${path}${url.search}`)
      if (denied || (mode === 'readback-denied' && writes.length)) return route.fulfill({ status: 403, json: { error: { message: 'Product review unavailable' } } })
      if (path.endsWith('/admin/products')) {
        const pageNumber = Number(url.searchParams.get('page') || 1), filter = url.searchParams.get('admin_hidden')
        if (mode === 'slow' && filter === 'true') await new Promise((resolve) => setTimeout(resolve, 500))
        const row = { ...detail(), id: pageNumber === 1 ? id : other, seller_id: url.searchParams.get('seller_id') || seller, name: mode === 'slow' && filter === 'true' ? 'Old filtered coat' : 'Linen coat', admin_hidden: filter === null ? hidden : filter === 'true' }
        return route.fulfill({ json: { data: mode === 'empty-list' ? [] : [row], pagination: { page: pageNumber, per_page: 25, total: mode === 'empty-list' ? 0 : 26 } } })
      }
      return route.fulfill({ json: { ...detail(), ...(mode === 'wrong-id' ? { id: other } : {}), ...(mode === 'missing-flag' ? { admin_hidden: undefined } : {}), ...(mode === 'readback-mismatch' && writes.length ? { admin_hidden: !hidden } : {}) } })
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return { reads, writes, allow: () => { denied = false }, change: (kind: string) => { if (kind === 'content') description = 'Updated product description.'; if (kind === 'restriction') hidden = !hidden; if (kind === 'seller') sellerStatus = 'suspended'; if (kind === 'stock') stock = 7; if (kind === 'price') price = '1600.25' } }
}
const open = (page: Page) => page.goto(`/admin/products/${id}`)
async function review(page: Page) { await page.getByRole('button', { name: /Review (hiding product|removing restriction)/ }).click() }
test('list filters/page/reset and invalid seller input use only supported API fields', async ({ page }, info) => {
  const state = await setup(page); await page.goto('/admin/products'); await expect(page.getByRole('link', { name: 'Review Linen coat' })).toHaveAttribute('href', `/admin/products/${id}`)
  await page.getByRole('button', { name: 'Next product page', exact: true }).click(); await expect(page.getByText('Page 2 of 2 · 26 products', { exact: true })).toBeVisible()
  await page.getByLabel('Seller reference (optional)', { exact: true }).fill(seller); await page.getByLabel('Admin restriction', { exact: true }).selectOption('true'); await page.getByRole('button', { name: 'Apply product filters', exact: true }).click()
  await expect(page.getByText('Page 1 of 2 · 26 products', { exact: true })).toBeVisible(); expect(state.reads).toContain(`/api/v1/admin/products?page=1&seller_id=${seller}&admin_hidden=true`)
  const before = state.reads.length; await page.getByLabel('Seller reference (optional)', { exact: true }).fill('invalid'); await page.getByRole('button', { name: 'Apply product filters', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('valid seller reference'); expect(state.reads).toHaveLength(before)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]); expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('admin-products.png'), fullPage: true }); expect(state.writes).toEqual([])
})
test('hide is reviewed, sent once and confirmed by its private detail readback', async ({ page }, info) => {
  const state = await setup(page); await open(page); await review(page); expect(state.writes).toEqual([])
  await expect(page.getByRole('link', { name: 'Fixture Label' })).toHaveAttribute('href', `/admin/sellers/${seller}`)
  await expect(page.getByText('PKR 1,200.75', { exact: true }).first()).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]); expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('admin-product-review.png'), fullPage: true })
  await page.getByRole('button', { name: 'Confirm product moderation', exact: true }).dblclick(); await expect(page.getByText('Product moderation change saved and confirmed.', { exact: true })).toBeVisible(); expect(state.writes).toEqual([`/api/v1/admin/products/${id}/hide`]); await expect(page.getByText('Published', { exact: true })).toBeVisible()
  expect(state.reads.every((path) => path.startsWith('/api/v1/admin/products/'))).toBe(true)
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toMatch(/fixture-token|Linen coat|1500\.25/)
})
for (const mode of ['hidden', 'draft', 'suspended', 'archived']) test(`unhide ${mode} does not promise publication or seller activation`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page); await expect(page.getByText('Remove only the administrative restriction. Other seller, publication and stock rules still apply.', { exact: true })).toBeVisible(); await page.getByRole('button', { name: 'Confirm product moderation', exact: true }).click(); await expect(page.getByText('Product moderation change saved and confirmed.', { exact: true })).toBeVisible(); expect(state.writes).toEqual([`/api/v1/admin/products/${id}/unhide`]); await expect(page.getByText('No admin restriction', { exact: true })).toBeVisible()
  if (mode === 'draft') await expect(page.getByText('Draft', { exact: true })).toBeVisible(); if (mode === 'suspended') await expect(page.getByText('Suspended', { exact: true })).toBeVisible(); if (mode === 'archived') await expect(page.getByText(/Archived account/)).toBeVisible()
})
for (const kind of ['content', 'restriction', 'seller', 'price']) test(`preflight catches changed ${kind}`, async ({ page }) => {
  const state = await setup(page); await open(page); await review(page); state.change(kind); await page.getByRole('button', { name: 'Confirm product moderation', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('changed'); expect(state.writes).toEqual([])
})
test('volatile stock updates do not block moderation or get overwritten', async ({ page }) => {
  const state = await setup(page); await open(page); await review(page); state.change('stock'); await page.getByRole('button', { name: 'Confirm product moderation', exact: true }).click(); await expect(page.getByText('Product moderation change saved and confirmed.', { exact: true })).toBeVisible(); expect(state.writes).toHaveLength(1); await expect(page.getByText('7', { exact: true })).toBeVisible()
})
for (const mode of ['lost', 'wrong-receipt', 'readback-mismatch', 'readback-denied']) test(`${mode} locks further writes across reload`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm product moderation', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); await page.reload(); await expect(page.getByText(/A moderation change is awaiting confirmation/)).toBeVisible(); const button = page.getByRole('button', { name: /Review (hiding product|removing restriction)/ }); if (await button.count()) await expect(button).toBeDisabled(); expect(state.writes).toHaveLength(1)
})
test('backing out never submits; a known rejection permits edits without replay', async ({ page }) => {
  const state = await setup(page, 'rejection'); await open(page); await review(page); await page.getByRole('button', { name: 'Back to moderation review', exact: true }).click(); expect(state.writes).toEqual([]); await review(page); await page.getByRole('button', { name: 'Confirm product moderation', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('cannot be changed'); await expect(page.getByRole('button', { name: 'Back to moderation review', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['wrong-id', 'missing-flag']) test(`${mode} blocks private moderation actions`, async ({ page }) => {
  await setup(page, mode); await open(page); await expect(page.getByRole('alert')).toContainText('could not be verified'); await expect(page.getByRole('button', { name: 'Review hiding product', exact: true })).toHaveCount(0)
})
test('empty lists and empty detail sections do not fabricate products or variants', async ({ page }) => {
  await setup(page, 'empty-list'); await page.goto('/admin/products'); await expect(page.getByText('No products on this page', { exact: true })).toBeVisible(); await expect(page.getByRole('button', { name: 'Next product page', exact: true })).toBeDisabled()
})
test('detail without images or variants is reviewable', async ({ page }) => {
  await setup(page, 'empty-detail'); await open(page); await expect(page.getByText('No product images supplied.', { exact: true })).toBeVisible(); await expect(page.getByText('No variants supplied.', { exact: true })).toBeVisible(); await expect(page.getByRole('button', { name: 'Review hiding product', exact: true })).toBeEnabled()
})
test('denied reads can be retried without assuming moderation state', async ({ page }) => {
  const state = await setup(page, 'denied'); await open(page); await expect(page.getByRole('alert')).toContainText('unavailable'); state.allow(); await page.getByRole('button', { name: 'Refresh product and discard review', exact: true }).click(); await expect(page.getByRole('button', { name: 'Review hiding product', exact: true })).toBeEnabled(); expect(state.writes).toEqual([])
})
test('stale list responses never replace current filters', async ({ page }) => {
  await setup(page, 'slow'); await page.goto('/admin/products'); await page.getByLabel('Admin restriction', { exact: true }).selectOption('true'); await page.getByRole('button', { name: 'Apply product filters', exact: true }).click(); await page.getByLabel('Admin restriction', { exact: true }).selectOption('false'); await page.getByRole('button', { name: 'Apply product filters', exact: true }).click(); await expect(page.getByRole('link', { name: 'Review Linen coat' })).toBeVisible(); await page.waitForTimeout(650); await expect(page.getByText('Old filtered coat', { exact: true })).toHaveCount(0)
})
for (const path of ['/admin/products/invalid', '/admin/products?seller_id=invalid', '/admin/products?page=0']) test(`${path} does not reach admin API`, async ({ page }) => {
  const state = await setup(page); await page.goto(path); await expect(page.getByRole('alert')).toBeVisible(); expect(state.reads).toEqual([])
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to moderate products'], ['customer', true, 'An administrator account is required'], ['seller', true, 'An administrator account is required'], ['Admin', true, 'An administrator account is required'], ['admin', false, 'Verify your email first']] as const) test(`${role} verified=${verified} has no moderation reads or writes`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading); expect(state.reads).toEqual([]); expect(state.writes).toEqual([])
})
