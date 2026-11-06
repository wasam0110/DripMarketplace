import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const seller = '11111111-1111-4111-8111-111111111111', id = '22222222-2222-4222-8222-222222222222', variantId = '33333333-3333-4333-8333-333333333333', categoryId = '44444444-4444-4444-8444-444444444444'
async function setup(page: Page, mode = 'ready', role = 'seller', verified = true) {
  let category: { id: string; name: string } | null = mode === 'missing-category' ? { id: '66666666-6666-4666-8666-666666666666', name: 'Archived category' } : null
  const variants = [{ id: variantId, sku: 'WHZ-TEST', size_type: 'alpha', size_value: 'M', colour: 'Blue', price: '2500.00', stock: 5, available_stock: 3, is_active: true }]
  const writes: { method: string; body: Record<string, unknown> }[] = [], reads: string[] = []
  const product = () => ({ id, seller_id: seller, name: 'Linen shirt', description: 'A lightweight linen shirt.', price: '2500.00', sale_price: null, meta_title: null, meta_description: null, category, variants })
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, email: 'seller@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.includes('/seller/')) reads.push(path)
    if (path.endsWith('/seller/me')) return route.fulfill({ json: { id: seller, brand_name: 'Fixture Label', status: mode === 'inactive' ? 'suspended' : 'active', registration_amount_due: '0.00', registration_paid_at: null } })
    if (path.endsWith('/categories')) return route.fulfill(mode === 'categories-failed' ? { status: 500, json: { error: { message: 'Categories unavailable' } } } : { json: { data: [{ id: categoryId, name: 'Shirts' }] } })
    if (path.includes('/seller/products')) {
      if (method === 'GET') return route.fulfill(mode === 'foreign' ? { json: { ...product(), seller_id: id } } : { json: product() })
      expect(route.request().headers().authorization).toBe('Bearer fixture-token')
      const body = route.request().postDataJSON(); writes.push({ method, body })
      if (mode === 'lost') return route.abort()
      if (mode === 'rejected') return route.fulfill({ status: 422, json: { error: { message: 'Variant validation failed' } } })
      if (method === 'PUT') { category = body.category_id ? { id: body.category_id, name: 'Shirts' } : null; return route.fulfill({ json: product() }) }
      if (method === 'POST') {
        variants.push({ ...variants[0], ...body, id: '55555555-5555-4555-8555-555555555555', sku: 'WHZ-NEW', stock: body.stock, available_stock: body.stock, price: String(body.price_override ?? '2500.00') })
        return route.fulfill({ json: product() })
      }
      if (mode === 'mismatch') return route.fulfill({ json: { ...variants[0], id: categoryId } })
      Object.assign(variants[0], body, Object.hasOwn(body, 'price_override') ? { price: String(body.price_override ?? '2500.00') } : {})
      return route.fulfill({ json: variants[0] })
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return { writes, reads }
}
const open = (page: Page) => page.goto(`/seller/products/${id}/options`)
test('assigns and clears category without changing other product fields', async ({ page }) => {
  const state = await setup(page); await open(page)
  await page.getByLabel('Product category').selectOption(categoryId); await page.getByRole('button', { name: 'Save category', exact: true }).click()
  await expect(page.getByText('Saved category: Shirts', { exact: true })).toBeVisible()
  await page.getByLabel('Product category').selectOption(''); await page.getByRole('button', { name: 'Save category', exact: true }).click()
  await expect(page.getByText('Saved category: Uncategorized', { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ method: 'PUT', body: { category_id: categoryId } }, { method: 'PUT', body: { category_id: null } }])
})
test('variant edits preserve stock and pricing unless explicitly changed', async ({ page }, info) => {
  const state = await setup(page); await open(page)
  await page.getByRole('button', { name: 'Edit variant WHZ-TEST', exact: true }).click()
  await page.getByLabel('Colour', { exact: true }).fill('Green')
  await page.getByRole('button', { name: 'Save variant', exact: true }).dblclick()
  await expect(page.getByText('Variant saved and confirmed.', { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ method: 'PATCH', body: { colour: 'Green' } }])
  await page.getByRole('button', { name: 'Edit variant WHZ-TEST', exact: true }).click()
  await page.getByLabel('Pricing action').selectOption('inherit'); await page.getByLabel('Variant active').uncheck()
  await page.getByRole('button', { name: 'Save variant', exact: true }).click()
  await expect(page.getByText('SKU: WHZ-TEST · Inactive', { exact: true })).toBeVisible()
  expect(state.writes[1]).toEqual({ method: 'PATCH', body: { is_active: false, price_override: null } })
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('product-options.png'), fullPage: true })
})
async function newVariant(page: Page) {
  await page.getByRole('button', { name: 'Add variant', exact: true }).click()
  await page.getByLabel('Size value', { exact: true }).fill('L'); await page.getByLabel('Colour', { exact: true }).fill('Black')
  await page.getByLabel('Initial stock', { exact: true }).fill('7')
}
test('creates a variant with initial stock and explicit override', async ({ page }) => {
  const state = await setup(page); await open(page); await newVariant(page)
  await page.getByLabel('Pricing action').selectOption('set'); await page.getByLabel('Price override (PKR)', { exact: true }).fill('3000')
  await page.getByRole('button', { name: 'Create variant', exact: true }).dblclick()
  await expect(page.getByText('SKU: WHZ-NEW · Active', { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ method: 'POST', body: { size_type: 'alpha', size_value: 'L', colour: 'Black', stock: 7, price_override: 3000 } }])
})
test('lost creation prevents another add after reload', async ({ page }) => {
  const state = await setup(page, 'lost'); await open(page); await newVariant(page)
  await page.getByRole('button', { name: 'Create variant', exact: true }).click()
  await expect(page.getByText(/A variant creation is pending/)).toBeVisible(); await page.reload()
  await expect(page.getByRole('button', { name: 'Add variant', exact: true })).toBeDisabled(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['lost', 'mismatch']) test(`${mode} update locks mutations through refresh`, async ({ page }) => {
  const state = await setup(page, mode); await open(page)
  await page.getByRole('button', { name: 'Edit variant WHZ-TEST', exact: true }).click(); await page.getByLabel('Colour', { exact: true }).fill('Red')
  await page.getByRole('button', { name: 'Save variant', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.getByRole('button', { name: 'Refresh saved options and discard edits' }).click()
  await expect(page.getByRole('button', { name: 'Add variant', exact: true })).toBeDisabled(); expect(state.writes).toHaveLength(1)
})
test('category read failure does not remove the saved category', async ({ page }) => {
  const state = await setup(page, 'categories-failed'); await open(page)
  await expect(page.getByRole('alert')).toContainText('Categories unavailable'); await expect(page.getByLabel('Product category')).toHaveCount(0); expect(state.writes).toEqual([])
})
test('an unavailable saved category is preserved until explicitly changed', async ({ page }) => {
  const state = await setup(page, 'missing-category'); await open(page)
  await expect(page.getByText('Saved category: Archived category', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Save category', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Refresh available categories' }).click()
  await expect(page.getByLabel('Product category')).toHaveValue('66666666-6666-4666-8666-666666666666')
  expect(state.writes).toEqual([])
})
test('invalid overrides and cancellation never write', async ({ page }) => {
  const state = await setup(page); await open(page); await newVariant(page)
  await page.getByLabel('Pricing action').selectOption('set'); await page.getByLabel('Price override (PKR)', { exact: true }).fill('99')
  await page.getByRole('button', { name: 'Create variant', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('The override must be')
  await page.getByRole('button', { name: 'Cancel variant edits' }).click()
  await expect(page.getByRole('heading', { name: 'New variant', exact: true })).toHaveCount(0); expect(state.writes).toEqual([])
})
test('definite rejection allows correction without automatic retry', async ({ page }) => {
  const state = await setup(page, 'rejected'); await open(page); await newVariant(page)
  await page.getByRole('button', { name: 'Create variant', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Variant validation failed'); await expect(page.getByRole('button', { name: 'Create variant', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['inactive', 'foreign']) test(`${mode} product is not editable`, async ({ page }) => {
  const state = await setup(page, mode); await open(page)
  await expect(page.getByText(mode === 'inactive' ? 'An active seller account is required to manage products.' : 'The product identity or details could not be verified.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Add variant', exact: true })).toHaveCount(0); expect(state.writes).toEqual([])
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to manage products'], ['customer', true, 'A seller account is required'], ['admin', true, 'A seller account is required'], ['seller', false, 'Verify your email first']] as const) test(`${role} verified=${verified} is gated`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page)
  await expect(page.getByRole('heading', { name: heading })).toBeVisible(); expect(state.reads).toEqual([])
})
