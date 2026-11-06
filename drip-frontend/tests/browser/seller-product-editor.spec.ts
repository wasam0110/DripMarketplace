import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const seller = '11111111-1111-4111-8111-111111111111', id = '22222222-2222-4222-8222-222222222222'
async function setup(page: Page, mode = 'ready', role = 'seller', verified = true) {
  let product = { id, seller_id: seller, name: 'Linen shirt', description: 'A lightweight linen shirt.', price: '2500.00', sale_price: '2000.00', meta_title: null, meta_description: null }
  const writes: { method: string; body: Record<string, unknown> }[] = []
  const reads: string[] = []
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, email: 'seller@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.includes('/seller/')) reads.push(path)
    if (path.endsWith('/seller/me')) return route.fulfill({ json: { id: seller, brand_name: 'Fixture Label', status: mode === 'inactive' ? 'suspended' : 'active', registration_amount_due: '0.00', registration_paid_at: null } })
    if (path.includes('/seller/products')) {
      if (method !== 'GET') {
        expect(route.request().headers().authorization).toBe('Bearer fixture-token')
        const body = route.request().postDataJSON(); writes.push({ method, body })
        if (mode === 'rejected') return route.fulfill({ status: 422, json: { error: { message: 'Product validation failed' } } })
        if (mode === 'lost') return route.abort()
        if (mode === 'mismatch') return route.fulfill({ json: { ...product, seller_id: id } })
        product = { ...product, ...body, price: String(body.price ?? product.price), sale_price: body.sale_price === undefined ? product.sale_price : body.sale_price === null ? null : String(body.sale_price) }
      }
      return route.fulfill(mode === 'denied' ? { status: 403, json: { error: { message: 'Product unavailable' } } } : { json: product })
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return { writes, reads }
}
test('edits changed fields only and clears optional price', async ({ page }, info) => {
  const state = await setup(page); await page.goto(`/seller/products/${id}/edit`)
  await expect(page.getByLabel('Product name')).toHaveValue('Linen shirt')
  await page.getByLabel('Sale price (PKR)', { exact: true }).fill('')
  await page.getByRole('button', { name: 'Save product details' }).dblclick()
  await expect(page.getByText('Product details saved and confirmed.', { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ method: 'PUT', body: { sale_price: null } }])
  await expect(page.getByLabel('Sale price (PKR)', { exact: true })).toHaveValue('')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('product-editor.png'), fullPage: true })
})
async function fillDraft(page: Page) {
  await page.getByLabel('Product name').fill('New linen shirt')
  await page.getByLabel('Description', { exact: true }).fill('A new lightweight linen shirt.')
  await page.getByLabel('Regular price (PKR)', { exact: true }).fill('3000')
}
test('creates one unpublished draft then opens its owned editor', async ({ page }) => {
  const state = await setup(page); await page.goto('/seller/products/new'); await fillDraft(page)
  await page.getByRole('button', { name: 'Create draft', exact: true }).dblclick()
  await expect(page).toHaveURL(new RegExp(`${id}/edit$`))
  expect(state.writes).toEqual([{ method: 'POST', body: { name: 'New linen shirt', description: 'A new lightweight linen shirt.', price: 3000, sale_price: null, meta_title: null, meta_description: null, is_published: false, variants: [] } }])
  expect(await page.evaluate(() => Object.keys(sessionStorage).some((key) => key.includes('product-create-pending')))).toBe(false)
})
test('lost creation stays locked across reload without storing the draft', async ({ page }) => {
  const state = await setup(page, 'lost'); await page.goto('/seller/products/new'); await fillDraft(page)
  await page.getByRole('button', { name: 'Create draft', exact: true }).click()
  await expect(page.getByText(/A draft submission is pending/)).toBeVisible()
  await page.reload(); await expect(page.getByRole('button', { name: 'Create draft', exact: true })).toBeDisabled()
  expect(state.writes).toHaveLength(1)
  expect(await page.evaluate(() => JSON.stringify({ ...sessionStorage, ...localStorage }))).not.toContain('New linen shirt')
})
for (const mode of ['lost', 'mismatch']) test(`${mode} update locks writes through read refresh`, async ({ page }) => {
  const state = await setup(page, mode); await page.goto(`/seller/products/${id}/edit`)
  await page.getByLabel('Product name').fill('Updated linen shirt'); await page.getByRole('button', { name: 'Save product details' }).click()
  await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.getByRole('button', { name: 'Refresh saved product and discard edits' }).click()
  await expect(page.getByRole('button', { name: 'Save product details' })).toBeDisabled(); expect(state.writes).toHaveLength(1)
})
test('definite validation rejection permits correction, not automatic replay', async ({ page }) => {
  const state = await setup(page, 'rejected'); await page.goto('/seller/products/new'); await fillDraft(page)
  await page.getByRole('button', { name: 'Create draft', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Product validation failed')
  await expect(page.getByRole('button', { name: 'Create draft', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
test('discard and local invalid pricing do not write', async ({ page }) => {
  const state = await setup(page); await page.goto(`/seller/products/${id}/edit`)
  await page.getByLabel('Regular price (PKR)', { exact: true }).fill('1000')
  await page.getByRole('button', { name: 'Save product details' }).click(); await expect(page.getByRole('alert')).toContainText('Sale price must be below')
  await page.getByRole('button', { name: 'Discard edits', exact: true }).click()
  await expect(page.getByLabel('Regular price (PKR)', { exact: true })).toHaveValue('2500'); expect(state.writes).toEqual([])
})
for (const mode of ['inactive', 'denied']) test(`${mode} cannot edit`, async ({ page }) => {
  await setup(page, mode); await page.goto(`/seller/products/${id}/edit`)
  await expect(page.getByText(mode === 'inactive' ? 'An active seller account is required to manage products.' : 'Product unavailable', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Product name')).toHaveCount(0)
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to manage products'], ['customer', true, 'A seller account is required'], ['admin', true, 'A seller account is required'], ['seller', false, 'Verify your email first']] as const) test(`${role} verified=${verified} is gated`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await page.goto('/seller/products/new')
  await expect(page.getByRole('heading', { name: heading })).toBeVisible(); expect(state.reads).toEqual([])
})
