import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const seller = '11111111-1111-4111-8111-111111111111', id = '22222222-2222-4222-8222-222222222222'
const imageId = (n: number) => `44444444-4444-4444-8444-${String(n).padStart(12, '0')}`
const img = (n: number) => ({ id: imageId(n), url: `https://images.example.test/${n}.webp`, alt_text: null, sort_order: n - 1, is_primary: n === 1 })
async function setup(page: Page, mode = 'ready', role = 'seller', verified = true) {
  let images = mode === 'empty' ? [] : mode === 'limit' ? Array.from({ length: 6 }, (_, i) => img(i + 1)) : mode === 'last' ? [img(1)] : [img(1), img(2)]
  let published = mode === 'last', writes = 0
  const calls: { method: string; path: string; body: unknown }[] = []
  const product = () => ({ id, seller_id: mode === 'foreign' ? id : seller, name: 'Linen shirt', description: 'A lightweight linen shirt.', price: '2500.00', sale_price: null, meta_title: null, meta_description: null, category: null, images, is_published: mode === 'missing-status' ? undefined : published,
    variants: [{ id: '33333333-3333-4333-8333-333333333333', sku: 'WHZ-TEST', size_type: 'alpha', size_value: 'M', colour: 'Blue', price: '2500.00', stock: 5, available_stock: 3, is_active: true }] })
  await page.route('https://images.example.test/**', (route) => route.fulfill({ status: 404, body: '' }))
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, email: 'seller@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.endsWith('/seller/me')) return route.fulfill({ json: { id: seller, brand_name: 'Fixture Label', status: mode === 'inactive' ? 'suspended' : 'active', registration_amount_due: '0.00', registration_paid_at: null } })
    if (path.includes('/seller/products')) {
      if (method === 'GET') return route.fulfill(mode === 'read-denied' && writes ? { status: 403, json: { error: { message: 'Read denied after save' } } } : { json: product() })
      writes++
      expect(route.request().headers().authorization).toBe('Bearer fixture-token')
      const multipart = route.request().headers()['content-type']?.includes('multipart/form-data')
      const body = multipart ? route.request().postData() : route.request().postData() ? route.request().postDataJSON() : null
      calls.push({ method, path, body })
      if (mode === 'lost') return route.abort()
      if (mode === 'rejected') return route.fulfill({ status: 422, json: { error: { message: 'No slots available' } } })
      if (mode === 'mismatch') return route.fulfill({ json: { message: 'Saved' } })
      if (multipart) { const added = img(3); images.push(added); return route.fulfill({ json: { images: [added] } }) }
      if (path.endsWith('/publish')) published = true
      if (path.endsWith('/unpublish')) published = false
      if (path.endsWith('/order')) images = (body as { image_ids: string[] }).image_ids.map((imageId, sort_order) => ({ ...images.find((row) => row.id === imageId)!, sort_order }))
      if (path.endsWith('/primary')) images = images.map((row) => ({ ...row, is_primary: path.includes(row.id) }))
      if (method === 'DELETE') { images = images.filter((row) => !path.endsWith(row.id)); if (images.length && !images.some((row) => row.is_primary)) images[0].is_primary = true; return route.fulfill({ status: 204 }) }
      return route.fulfill({ json: { message: 'Saved' } })
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return calls
}
const open = (page: Page) => page.goto(`/seller/products/${id}/media`)
async function file(page: Page) {
  const base64 = await page.evaluate(() => { const canvas = document.createElement('canvas'); canvas.width = 24; canvas.height = 24; const ctx = canvas.getContext('2d')!; ctx.fillStyle = '#203C32'; ctx.fillRect(0, 0, 24, 24); return canvas.toDataURL('image/png').split(',')[1] })
  return { name: 'test-product.png', mimeType: 'image/png', buffer: Buffer.from(base64, 'base64') }
}
test('uploads one multipart image only after explicit confirmation', async ({ page }, info) => {
  const calls = await setup(page); await open(page)
  await page.getByLabel('Choose product image').setInputFiles(await file(page))
  await expect(page.getByAltText('Selected product image preview')).toBeVisible(); expect(calls).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('product-media.png'), fullPage: true })
  await page.getByRole('button', { name: 'Upload selected image' }).dblclick()
  await expect(page.getByText('Image uploaded and confirmed.', { exact: true })).toBeVisible()
  expect(calls).toHaveLength(1); expect(calls[0].body).toContain('name="images"'); expect(calls[0].body).not.toContain('name="logo"')
  await expect(page.getByRole('heading', { name: 'Saved images (3/6)' })).toBeVisible()
})
test('sets primary, reorders the full image set and explicitly removes an attachment', async ({ page }) => {
  const calls = await setup(page); await open(page)
  await page.getByRole('button', { name: 'Make image 2 primary' }).click(); await expect(page.getByText('Primary image saved and confirmed.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Move image 2 earlier' }).click(); await expect(page.getByText('Image order saved and confirmed.', { exact: true })).toBeVisible()
  expect(calls[1].body).toEqual({ image_ids: [imageId(2), imageId(1)] })
  await page.getByRole('button', { name: 'Remove image 2', exact: true }).click(); expect(calls).toHaveLength(2)
  await page.getByRole('button', { name: 'Cancel change' }).click(); expect(calls).toHaveLength(2)
  await page.getByRole('button', { name: 'Remove image 2', exact: true }).click(); await page.getByRole('button', { name: 'Confirm image removal', exact: true }).click()
  await expect(page.getByText('Image removal confirmed.', { exact: true })).toBeVisible(); expect(calls[2].method).toBe('DELETE')
})
test('publish and unpublish require explicit confirmation and saved-state reads', async ({ page }) => {
  const calls = await setup(page); await open(page)
  await page.getByRole('button', { name: 'Publish product', exact: true }).click(); expect(calls).toEqual([])
  await page.getByRole('button', { name: 'Confirm publish', exact: true }).dblclick()
  await expect(page.getByText('Saved publication state: Published', { exact: true })).toBeVisible(); expect(calls).toHaveLength(1)
  await page.getByRole('button', { name: 'Unpublish product', exact: true }).click(); await page.getByRole('button', { name: 'Confirm unpublish', exact: true }).click()
  await expect(page.getByText('Saved publication state: Draft', { exact: true })).toBeVisible(); expect(calls).toHaveLength(2)
})
for (const mode of ['lost', 'mismatch', 'read-denied']) test(`${mode} publication stays locked through refresh`, async ({ page }) => {
  const calls = await setup(page, mode); await open(page)
  await page.getByRole('button', { name: 'Publish product', exact: true }).click(); await page.getByRole('button', { name: 'Confirm publish', exact: true }).click()
  await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.getByRole('button', { name: 'Refresh saved media and discard selection' }).click()
  await expect(page.getByText(/Further changes are locked/)).toBeVisible(); expect(calls).toHaveLength(1)
})
test('known publication rejection stays editable without replay', async ({ page }) => {
  const calls = await setup(page, 'rejected'); await open(page)
  await page.getByRole('button', { name: 'Publish product', exact: true }).click(); await page.getByRole('button', { name: 'Confirm publish', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('No slots available'); await expect(page.getByRole('button', { name: 'Confirm publish', exact: true })).toBeEnabled(); expect(calls).toHaveLength(1)
})
test('invalid file and discarded selection never upload', async ({ page }) => {
  const calls = await setup(page); await open(page)
  await page.getByLabel('Choose product image').setInputFiles({ name: 'bad.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg/>') })
  await expect(page.getByRole('alert')).toContainText('Choose a non-empty')
  await page.getByLabel('Choose product image').setInputFiles(await file(page)); await expect(page.getByAltText('Selected product image preview')).toBeVisible()
  await page.getByRole('button', { name: 'Discard selected image' }).click(); await expect(page.getByRole('button', { name: 'Upload selected image' })).toBeDisabled(); expect(calls).toEqual([])
})
for (const [mode, button] of [['last', 'Remove image 1'], ['empty', 'Publish product']] as const) test(`${mode} state prevents invalid action`, async ({ page }) => {
  const calls = await setup(page, mode); await open(page); await expect(page.getByRole('button', { name: button, exact: true })).toBeDisabled(); expect(calls).toEqual([])
})
test('six-image capacity blocks selection', async ({ page }) => { await setup(page, 'limit'); await open(page); await expect(page.getByLabel('Choose product image')).toBeDisabled() })
for (const mode of ['missing-status', 'foreign', 'inactive']) test(`${mode} does not mount writable media`, async ({ page }) => {
  const calls = await setup(page, mode); await open(page)
  await expect(page.getByText(mode === 'missing-status' ? 'Publication status is unavailable. Update the backend before using these controls.' : mode === 'foreign' ? 'The product identity or details could not be verified.' : 'An active seller account is required to manage products.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Choose product image')).toHaveCount(0); expect(calls).toEqual([])
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to manage products'], ['customer', true, 'A seller account is required'], ['admin', true, 'A seller account is required'], ['seller', false, 'Verify your email first']] as const) test(`${role} verified=${verified} is gated`, async ({ page }) => {
  await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { name: heading })).toBeVisible(); await expect(page.getByLabel('Choose product image')).toHaveCount(0)
})
