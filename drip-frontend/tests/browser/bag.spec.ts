import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const productId = '11111111-1111-4111-8111-111111111111'
const variantId = '22222222-2222-4222-8222-222222222222'
const product = {
  id: productId, name: 'Linen overshirt', slug: 'linen-overshirt', brand_name: 'Studio Label',
  price: '4000', sale_price: null, primary_image: null, has_stock: true,
  description: 'A relaxed linen layer.', avg_rating: 0, review_count: 0, images: [],
  seller: { id: 'seller-1', slug: 'studio-label', brand_name: 'Studio Label', return_policy: 'Return within seven days.' },
  variants: [
    { id: variantId, sku: 'WHZ-1', size_type: 'alpha', size_value: 'M', colour: 'Ivory', price: '4500', stock: 3, available_stock: 3, is_active: true },
    { id: '33333333-3333-4333-8333-333333333333', sku: 'WHZ-2', size_type: 'alpha', size_value: 'L', colour: 'Ivory', price: '4500', stock: 0, available_stock: 0, is_active: true },
  ],
}
const cart = (quantity: number) => ({
  items: quantity ? [{
    variant_id: variantId, product_id: productId, product_name: product.name, brand_name: product.brand_name,
    brand_color: '#203C32', primary_image: null, size: 'M', colour: 'Ivory', unit_price: '4500',
    quantity, subtotal: String(quantity * 4500), available_stock: 3, seller_id: 'seller-1',
  }] : [],
  item_count: quantity, subtotal: String(quantity * 4500), shipping_fee: quantity ? '250' : '0', total: String(quantity ? quantity * 4500 + 250 : 0),
})
async function setup(page: Page, failQuote = false) {
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.includes('/auth/')) return route.fulfill({ status: 401, json: { error: { message: 'Please sign in.' } } })
    if (path.endsWith(`/products/${productId}`)) return route.fulfill({ json: product })
    if (path.endsWith('/orders/guest/quote')) {
      if (failQuote) return route.fulfill({ status: 409, json: { error: { message: 'This selection is unavailable.' } } })
      return route.fulfill({ json: cart(route.request().postDataJSON().items[0]?.quantity ?? 0) })
    }
    return route.fulfill({ json: { data: [], pagination: { has_next: false, next_cursor: null, limit: 20 } } })
  })
}
test('guest selects a stocked variant, persists bag, changes quantity and removes', async ({ page }, info) => {
  // This journey includes two complete accessibility scans and a persistence reload.
  test.setTimeout(60000)
  await setup(page)
  await page.goto(`/products/${productId}`)
  const add = page.getByRole('button', { name: 'Add to bag', exact: true })
  await expect(add).toBeDisabled()
  await expect(page.getByRole('button', { name: 'L — sold out' })).toBeDisabled()
  await page.getByRole('button', { name: 'M', exact: true }).click()
  await expect(page.locator('.product-detail .lead')).toContainText('4,500')
  await expect(add).toBeEnabled()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.locator('#main').focus()
  await page.screenshot({ path: info.outputPath('product.png'), fullPage: true })
  await add.click()
  await page.getByRole('link', { name: 'View bag', exact: true }).click()
  await expect(page.locator('.bag-total')).toContainText('4,750')
  await page.reload()
  const quantity = page.getByRole('combobox', { name: /Quantity for/ })
  await expect(quantity).toHaveValue('1')
  await quantity.selectOption('2')
  await expect(page.locator('.bag-total')).toContainText('9,250')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('bag.png'), fullPage: true })
  await page.getByRole('button', { name: /^Remove Linen/ }).click()
  await expect(page.getByText('Room for something good.')).toBeVisible()
})
test('failed guest quote preserves selections and allows explicit removal', async ({ page }) => {
  await setup(page, true)
  await page.addInitScript(({ productId, variantId }) => {
    localStorage.setItem('wearhowz.guest-bag.v1', JSON.stringify([{ product_id: productId, variant_id: variantId, quantity: 1 }]))
  }, { productId, variantId })
  await page.goto('/bag')
  await expect(page.getByRole('alert')).toContainText('This selection is unavailable.')
  await expect(page.getByText('Your summary', { exact: true })).not.toBeVisible()
  await page.getByRole('button', { name: 'Remove saved piece' }).click()
  await expect(page.getByText('Room for something good.')).toBeVisible()
})

async function setupAccount(page: Page, uncertainWrite = false) {
  let quantity = 1
  let writes = 0
  let merges = 0
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: {
      id: 'account-1', email: 'fixture@example.test', role: 'customer', first_name: 'Test', last_name: 'Customer', has_verified_email: true,
    } })
    if (path.endsWith(`/products/${productId}`)) return route.fulfill({ json: product })
    if (path.endsWith('/cart/sync')) {
      merges++
      quantity = Math.max(quantity, route.request().postDataJSON().items[0].quantity)
      return route.fulfill({ json: cart(quantity) })
    }
    if (path.endsWith('/cart') && route.request().method() === 'POST') {
      writes++
      quantity += route.request().postDataJSON().quantity
      if (uncertainWrite) return route.abort('failed')
      return route.fulfill({ json: cart(quantity) })
    }
    if (path.endsWith('/cart')) return route.fulfill({ json: cart(quantity) })
    return route.fulfill({ status: 404, json: { error: { message: 'Unexpected fixture route' } } })
  })
  return { writes: () => writes, merges: () => merges }
}

test('signed-in user explicitly merges guest bag using maximum quantity', async ({ page }) => {
  const calls = await setupAccount(page)
  await page.addInitScript(({ productId, variantId }) => {
    localStorage.setItem('wearhowz.guest-bag.v1', JSON.stringify([{ product_id: productId, variant_id: variantId, quantity: 2 }]))
  }, { productId, variantId })
  await page.goto('/bag')
  const merge = page.getByRole('button', { name: 'Merge guest bag' })
  await expect(merge).toBeEnabled()
  expect(calls.merges()).toBe(0)
  await merge.click()
  await expect(page.getByRole('combobox', { name: /Quantity for/ })).toHaveValue('2')
  await expect(merge).not.toBeVisible()
  expect(calls.merges()).toBe(1)
  expect(await page.evaluate(() => localStorage.getItem('wearhowz.guest-bag.v1'))).toBeNull()
})

test('ambiguous signed-in add is never replayed and requires a fresh read', async ({ page }) => {
  const calls = await setupAccount(page, true)
  await page.goto(`/products/${productId}`)
  await page.getByRole('button', { name: 'M', exact: true }).click()
  const add = page.getByRole('button', { name: 'Add to bag', exact: true })
  await expect(add).toBeEnabled()
  await add.click()
  await expect(page.locator('.product-detail').getByRole('alert')).toBeVisible()
  await expect(add).toBeDisabled()
  expect(calls.writes()).toBe(1)
  await page.getByRole('link', { name: 'Review your bag before another change' }).click()
  await page.getByRole('button', { name: 'Refresh bag' }).click()
  await expect(page.getByRole('combobox', { name: /Quantity for/ })).toHaveValue('2')
  expect(calls.writes()).toBe(1)
})
