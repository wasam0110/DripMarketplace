import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const selection = { product_id: '11111111-1111-4111-8111-111111111111', variant_id: '22222222-2222-4222-8222-222222222222', quantity: 1 }
const quote = {
  items: [{ ...selection, product_name: 'Linen overshirt', brand_name: 'Studio Label', brand_color: '#203c32', primary_image: null, size: 'M', colour: 'Ivory', unit_price: '4500', subtotal: '4500', available_stock: 3, seller_id: 'seller-1' }],
  item_count: 1, subtotal: '4500', discount_amount: '0', shipping_fee: '250', total: '4750', currency: 'PKR',
  payment_methods: [{ method: 'cod', available: true, unavailable_reason: null }, { method: 'payfast', available: false, unavailable_reason: 'Unavailable' }],
}
async function setup(page: Page, options: { account?: boolean; cod?: boolean; fail?: boolean } = {}) {
  const requests: { path: string; body: unknown }[] = []
  await page.addInitScript((item) => localStorage.setItem('wearhowz.guest-bag.v1', JSON.stringify([item])), selection)
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    const body = route.request().postData() ? route.request().postDataJSON() : null
    requests.push({ path, body })
    if (path.endsWith('/auth/refresh')) return route.fulfill(options.account ? { json: { access_token: 'fixture' } } : { status: 401, json: { error: { message: 'Guest' } } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'account-1', email: 'account@example.test', role: 'customer' } })
    if (path.endsWith('/cart')) return route.fulfill({ json: quote })
    if (path.endsWith('/orders/guest/quote')) {
      if (options.fail) return route.fulfill({ status: 409, json: { error: { message: 'Stock changed. Review the bag.' } } })
      return route.fulfill({ json: { ...quote, payment_methods: [{ method: 'cod', available: options.cod !== false, unavailable_reason: 'COD limit exceeded' }] } })
    }
    if (path.endsWith('/coupons/validate')) return route.fulfill(body.code === 'SAVE' ? { json: { code: 'SAVE', discount_amount: '450', new_subtotal: '4050' } } : { status: 400, json: { error: { message: 'Coupon code not found' } } })
    return route.fulfill({ status: 500, json: { error: { message: `Forbidden unexpected request: ${path}` } } })
  })
  return requests
}
async function fillDetails(page: Page, guest = true) {
  if (guest) await page.getByLabel('Email address', { exact: true }).fill('guest@example.test')
  await page.getByLabel('Recipient name').fill('Test Customer')
  await page.getByLabel('Mobile number').fill('03001234567')
  await page.getByLabel('Street address').fill('42 Test Street')
  await page.getByLabel('City', { exact: true }).fill('Karachi')
  await page.getByLabel('Province', { exact: true }).selectOption('Sindh')
}
test('guest details, payment and review remain private and cannot submit an order', async ({ page }, info) => {
  test.setTimeout(60000)
  const requests = await setup(page)
  await page.goto('/checkout')
  await expect(page.getByLabel('Email address', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Continue to payment' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Where should we send it?')
  await fillDetails(page)
  await page.getByLabel('Mobile number').fill('123')
  await page.getByRole('button', { name: 'Continue to payment' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Where should we send it?')
  await page.getByLabel('Mobile number').fill('03001234567')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('checkout-details.png'), fullPage: true })
  await page.getByRole('button', { name: 'Continue to payment' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Choose your payment')
  await expect(page.getByRole('radio', { name: /Pay online/ })).toBeDisabled()
  await page.getByRole('radio', { name: /Cash on delivery/ }).check()
  await page.getByRole('button', { name: 'Review your order' }).click()
  await expect(page.getByRole('heading', { name: 'One last look' })).toBeFocused()
  await expect(page.getByRole('button', { name: /Place order/ })).toBeDisabled()
  await expect(page.locator('.checkout-form address')).toContainText('42 Test Street')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('checkout-review.png'), fullPage: true })
  expect(requests.filter(({ path }) => /\/orders(\/guest)?$|\/payments\//.test(path))).toEqual([])
  expect(JSON.stringify(requests)).not.toContain('guest@example.test')
  expect(JSON.stringify(requests)).not.toContain('42 Test Street')
  const storage = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))
  expect(storage).not.toContain('guest@example.test')
  expect(storage).not.toContain('42 Test Street')
  await page.reload()
  await expect(page.getByLabel('Recipient name')).toHaveValue('')
})
test('signed-in coupon preview uses server amounts and resets on refresh', async ({ page }) => {
  const requests = await setup(page, { account: true })
  await page.goto('/checkout')
  await expect(page.getByText('Signed in as account@example.test')).toBeVisible()
  await page.getByLabel('Promo code').fill('BAD')
  await page.getByRole('button', { name: 'Apply code' }).click()
  await expect(page.getByRole('alert')).toContainText('Coupon code not found')
  await page.getByLabel('Promo code').fill('SAVE')
  await page.getByRole('button', { name: 'Apply code' }).click()
  await expect(page.locator('.bag-total')).toContainText('4,300')
  expect(requests.find(({ path, body }) => path.endsWith('/coupons/validate') && (body as { code: string }).code === 'SAVE')?.body).toEqual({ code: 'SAVE', subtotal: '4500' })
  await page.getByRole('button', { name: 'Refresh prices' }).click()
  await expect(page.locator('.bag-total')).toContainText('4,750')
  await expect(page.getByText('SAVE applied to this preview.')).not.toBeVisible()
})
test('unavailable COD cannot advance to review', async ({ page }) => {
  await setup(page, { cod: false })
  await page.goto('/checkout')
  await fillDetails(page)
  await page.getByRole('button', { name: 'Continue to payment' }).click()
  await expect(page.getByRole('radio', { name: /Cash on delivery/ })).toBeDisabled()
  await expect(page.getByText('COD limit exceeded')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Review your order' })).toBeDisabled()
})
test('failed quote never exposes a checkout form or guessed totals', async ({ page }) => {
  await setup(page, { fail: true })
  await page.goto('/checkout')
  await expect(page.getByRole('alert')).toContainText('Stock changed')
  await expect(page.getByLabel('Recipient name')).not.toBeVisible()
  await expect(page.getByText('Order summary', { exact: true })).not.toBeVisible()
})
