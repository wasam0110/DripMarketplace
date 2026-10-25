import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const selection = { product_id: '11111111-1111-4111-8111-111111111111', variant_id: '22222222-2222-4222-8222-222222222222', quantity: 1 }
const quote = {
  items: [{ ...selection, product_name: 'Linen overshirt', brand_name: 'Studio Label', brand_color: '#203c32', primary_image: null, size: 'M', colour: 'Ivory', unit_price: '4500', subtotal: '4500', available_stock: 3, seller_id: 'seller-1' }],
  item_count: 1, subtotal: '4500', discount_amount: '0', shipping_fee: '250', total: '4750', currency: 'PKR',
  quote_token: 'signed-fixture', quote_expires_at: '2030-01-01T00:00:00Z',
  payment_methods: [{ method: 'cod', available: true, unavailable_reason: null }, { method: 'payfast', available: false, unavailable_reason: 'Unavailable' }],
}
const order = { order_id: '33333333-3333-4333-8333-333333333333', order_number: 'WHZ-TEST-1', status: 'pending_cod_verification', total: '4750', payment_method: 'cod', guest_token: 'private-guest-token', whatsapp_url: 'https://wa.me/923001234567?text=WHZ-TEST-1' }
async function setup(page: Page, options: { account?: boolean; cod?: boolean; fail?: boolean; lost?: boolean; changed?: boolean; expired?: boolean; recoveryExpired?: boolean } = {}) {
  const requests: { path: string; body: unknown }[] = []
  let submissions = 0
  await page.addInitScript((item) => localStorage.setItem('wearhowz.guest-bag.v1', JSON.stringify([item])), selection)
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    const body = route.request().postData() ? route.request().postDataJSON() : null
    requests.push({ path, body })
    if (path.endsWith('/auth/refresh')) return route.fulfill(options.account ? { json: { access_token: 'fixture' } } : { status: 401, json: { error: { message: 'Guest' } } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'account-1', email: 'account@example.test', role: 'customer' } })
    if (path.endsWith('/cart')) return route.fulfill({ json: quote })
    if (path.endsWith('/me/addresses')) return route.fulfill({ json: [] })
    if (path === `/api/v1/orders/${order.order_id}`) {
      expect(route.request().headers()['x-guest-token']).toBe('private-guest-token')
      return route.fulfill({ json: { id: order.order_id, order_number: order.order_number,
        status: order.status, payment_method: 'cod', created_at: '2026-10-21T01:00:00Z',
        subtotal: '4500', shipping_fee: '250', discount_amount: '0', total: '4750',
        address: null, items: [], seller_orders: [], notes: null } })
    }
    if (path.endsWith('/orders/guest/quote') || path.endsWith('/orders/quote')) {
      if (options.fail) return route.fulfill({ status: 409, json: { error: { message: 'Stock changed. Review the bag.' } } })
      if (body.coupon_code && body.coupon_code !== 'SAVE') return route.fulfill({ status: 422, json: { error: { message: 'Coupon code not found' } } })
      return route.fulfill({ json: { ...quote,
        ...(body.coupon_code === 'SAVE' ? { discount_amount: '450', total: '4300', quote_token: 'signed-discount' } : {}),
        ...(options.changed && submissions ? { total: '5000', subtotal: '4750', items: [{ ...quote.items[0], unit_price: '4750', subtotal: '4750' }], quote_token: 'new-price-quote' } : {}),
        ...(options.expired ? { quote_expires_at: '2020-01-01T00:00:00Z' } : {}),
        payment_methods: [{ method: 'cod', available: options.cod !== false, unavailable_reason: 'COD limit exceeded' }] } })
    }
    if (path.endsWith('/recover')) return options.recoveryExpired
      ? route.fulfill({ status: 409, json: { error: { code: 'CHECKOUT_RECOVERY_EXPIRED', message: 'Guest recovery has expired. Contact support.' } } })
      : route.fulfill({ json: order })
    if (/\/orders(\/guest)?$/.test(path)) {
      submissions += 1
      if (options.changed && submissions === 1) return route.fulfill({ status: 409, json: { error: { code: 'CHECKOUT_QUOTE_CHANGED', message: 'Prices changed. Review the new quote.' } } })
      if (options.lost && submissions === 1) return route.abort('failed')
      return route.fulfill({ status: 201, json: { ...order, total: options.changed ? '5000' : body.coupon_code ? '4300' : '4750' } })
    }
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

test('saved address is copied explicitly and only the reviewed snapshot is submitted', async ({ page }, info) => {
  const requests = await setup(page, { account: true })
  const saved = { id: '44444444-4444-4444-8444-444444444444', label: 'Office', street: '123 Saved Street', city: 'Gilgit', province: 'Gilgit Baltistan', is_default: true }
  const addressCalls: string[] = []
  await page.route('**/me/addresses', (route) => {
    addressCalls.push(route.request().method())
    expect(route.request().headers().authorization).toBe('Bearer fixture')
    return route.fulfill({ json: [saved] })
  })
  await page.goto('/checkout')
  await expect(page.getByLabel('Saved delivery address')).toBeVisible()
  await expect(page.getByLabel('Street address', { exact: true })).toHaveValue('')
  await fillDetails(page, false)
  await page.getByLabel('Delivery note (optional)').fill('Call on arrival')
  await page.getByLabel('Saved delivery address').selectOption(saved.id)
  await expect(page.getByLabel('Street address', { exact: true })).toHaveValue('42 Test Street')
  await page.getByRole('button', { name: 'Use selected address' }).click()
  await expect(page.getByLabel('Street address', { exact: true })).toHaveValue(saved.street)
  await expect(page.getByLabel('Province', { exact: true })).toHaveValue(saved.province)
  await expect(page.getByLabel('Recipient name')).toHaveValue('Test Customer')
  await expect(page.getByLabel('Mobile number')).toHaveValue('03001234567')
  await expect(page.getByLabel('Delivery note (optional)')).toHaveValue('Call on arrival')
  await page.getByLabel('Street address', { exact: true }).fill('789 Reviewed Street')
  await page.getByRole('button', { name: 'Refresh saved addresses' }).click()
  await expect(page.getByLabel('Saved delivery address')).toBeVisible()
  await expect(page.getByLabel('Street address', { exact: true })).toHaveValue('789 Reviewed Street')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('saved-address-checkout.png'), fullPage: true })
  expect(requests.filter(({ path }) => path === '/api/v1/orders')).toEqual([])
  await page.getByRole('button', { name: 'Continue to payment' }).click()
  await page.getByRole('radio', { name: /Cash on delivery/ }).check()
  await page.getByRole('button', { name: 'Review your order' }).click()
  await expect(page.locator('.checkout-form address')).toContainText('789 Reviewed Street')
  await page.getByRole('button', { name: /Place order/ }).click()
  await expect(page.getByRole('heading', { name: /Your order:/ })).toBeVisible()
  const placed = requests.find(({ path }) => path === '/api/v1/orders')!.body as { shipping_address: unknown }
  expect(placed.shipping_address).toEqual({ recipient_name: 'Test Customer', phone: '03001234567', street: '789 Reviewed Street', city: 'Gilgit', province: 'Gilgit Baltistan', note: 'Call on arrival' })
  expect(addressCalls.every((method) => method === 'GET')).toBe(true)
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))).not.toMatch(/Saved Street|Reviewed Street|Call on arrival/)
})

test('failed saved-address reads allow manual delivery and explicit retry', async ({ page }) => {
  await setup(page, { account: true })
  let failed = true
  await page.route('**/me/addresses', (route) => route.fulfill(failed ? { status: 503, json: { error: { message: 'Saved addresses unavailable.' } } } : { json: [] }))
  await page.goto('/checkout')
  await expect(page.getByText('You can still enter delivery details manually.')).toBeVisible()
  await fillDetails(page, false)
  failed = false
  await page.getByRole('button', { name: 'Refresh saved addresses' }).click()
  await expect(page.getByText('No saved addresses. Enter your delivery details below.')).toBeVisible()
  await expect(page.getByLabel('Street address', { exact: true })).toHaveValue('42 Test Street')
  await page.getByRole('button', { name: 'Continue to payment' }).click()
  await expect(page.getByRole('heading', { name: 'Choose your payment', exact: true })).toBeVisible()
})

test('guests do not read saved addresses', async ({ page }) => {
  const requests = await setup(page)
  await page.goto('/checkout')
  await expect(page.getByLabel('Email address', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Saved delivery address')).not.toBeVisible()
  expect(requests.filter(({ path }) => path.endsWith('/me/addresses'))).toEqual([])
})
test('details stay private until explicit placement and review is accessible', async ({ page }, info) => {
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
  await expect(page.getByRole('button', { name: /Place order/ })).toBeEnabled()
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
  expect(requests.find(({ path, body }) => path.endsWith('/orders/quote') && (body as { coupon_code?: string }).coupon_code === 'SAVE')?.body).toEqual({ coupon_code: 'SAVE', payment_method: 'cod' })
  await page.getByRole('button', { name: 'Refresh prices' }).click()
  await expect(page.locator('.bag-total')).toContainText('4,750')
  await expect(page.getByText('SAVE applied to this quote.')).not.toBeVisible()
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

async function review(page: Page, guest = true) {
  await fillDetails(page, guest)
  await page.getByRole('button', { name: 'Continue to payment' }).click()
  await page.getByRole('radio', { name: /Cash on delivery/ }).check()
  await page.getByRole('button', { name: 'Review your order' }).click()
}
const creates = (requests: { path: string; body: unknown }[]) => requests.filter(({ path }) => /\/orders(\/guest)?$/.test(path))

test('guest places COD once, sees real confirmation and can recover after reload', async ({ page }) => {
  const requests = await setup(page)
  await page.goto('/checkout')
  await review(page)
  await page.getByRole('button', { name: /Place order/ }).click()
  await expect(page.getByRole('heading', { name: 'Your order: WHZ-TEST-1' })).toBeVisible()
  expect(creates(requests)).toHaveLength(1)
  expect(creates(requests)[0].body).toMatchObject({ quote_token: 'signed-fixture', payment_method: 'cod', guest_email: 'guest@example.test' })
  expect(await page.evaluate(() => localStorage.getItem('wearhowz.guest-bag.v1'))).toBeNull()
  const storage = await page.evaluate(() => JSON.stringify({ ...sessionStorage }))
  expect(storage).not.toContain('guest@example.test')
  expect(storage).not.toContain('private-guest-token')
  expect(storage).not.toContain('42 Test Street')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Recover your checkout' })).toBeVisible()
  await page.getByRole('button', { name: 'Check order status' }).click()
  await expect(page.getByRole('heading', { name: 'Your order: WHZ-TEST-1' })).toBeVisible()
  expect(creates(requests)).toHaveLength(1)
})

test('checkout confirmation hands guest access to tracking without URL or storage tokens', async ({ page }) => {
  await setup(page)
  await page.goto('/checkout')
  await review(page)
  await page.getByRole('button', { name: /Place order/ }).click()
  await page.getByRole('button', { name: 'View order details' }).click()
  await expect(page.getByRole('heading', { name: 'Order WHZ-TEST-1' })).toBeVisible()
  expect(page.url()).not.toContain('private-guest-token')
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage }, history: history.state }))).not.toContain('private-guest-token')
  await page.reload()
  await expect(page.getByLabel('Private guest access code')).toBeVisible()
})

test('lost response retries the identical order without generating a new key', async ({ page }) => {
  const requests = await setup(page, { lost: true })
  await page.goto('/checkout')
  await review(page)
  await page.getByRole('button', { name: /Place order/ }).click()
  await expect(page.getByRole('alert')).toContainText('connect')
  await page.getByRole('button', { name: 'Retry the same order' }).click()
  await expect(page.getByRole('heading', { name: 'Your order: WHZ-TEST-1' })).toBeVisible()
  expect(creates(requests)).toHaveLength(2)
  expect(creates(requests)[0].body).toEqual(creates(requests)[1].body)
})

test('a changed price requires a new explicit review before another submission', async ({ page }) => {
  const requests = await setup(page, { changed: true })
  await page.goto('/checkout')
  await review(page)
  await page.getByRole('button', { name: /Place order/ }).click()
  await expect(page.getByRole('alert')).toContainText('Prices changed')
  await expect(page.locator('.bag-total')).toContainText('5,000')
  expect(creates(requests)).toHaveLength(1)
  await expect(page.getByRole('heading', { name: 'Where should we send it?' })).toBeVisible()
  await review(page)
  await page.getByRole('button', { name: /Place order/ }).click()
  await expect(page.getByRole('heading', { name: 'Your order: WHZ-TEST-1' })).toBeVisible()
  expect(creates(requests)[1].body).toMatchObject({ quote_token: 'new-price-quote' })
})

test('account coupon is included in the signed quote and authenticated order', async ({ page }) => {
  const requests = await setup(page, { account: true })
  await page.goto('/checkout')
  await page.getByLabel('Promo code').fill('SAVE')
  await page.getByRole('button', { name: 'Apply code' }).click()
  await expect(page.locator('.bag-total')).toContainText('4,300')
  await review(page, false)
  await page.getByRole('button', { name: /Place order/ }).click()
  await expect(page.getByRole('heading', { name: 'Your order: WHZ-TEST-1' })).toBeVisible()
  expect(creates(requests)[0]).toMatchObject({ path: '/api/v1/orders', body: { coupon_code: 'SAVE', quote_token: 'signed-discount' } })
  expect(creates(requests)[0].body).not.toHaveProperty('guest_email')
  expect(creates(requests)[0].body).not.toHaveProperty('items')
})

test('an expired quote never submits and restarts review', async ({ page }) => {
  const requests = await setup(page, { expired: true })
  await page.goto('/checkout')
  await review(page)
  await page.getByRole('button', { name: /Place order/ }).click()
  await expect(page.getByRole('heading', { name: 'Where should we send it?' })).toBeVisible()
  expect(creates(requests)).toHaveLength(0)
})

test('expired guest recovery stays blocked rather than allowing another order', async ({ page }) => {
  const requests = await setup(page, { recoveryExpired: true })
  await page.addInitScript(() => sessionStorage.setItem('wearhowz.checkout.v1:guest', '11111111-1111-4111-8111-111111111111'))
  await page.goto('/checkout')
  await page.getByRole('button', { name: 'Check order status' }).click()
  await expect(page.getByRole('alert')).toContainText('expired')
  await expect(page.getByRole('button', { name: /Place order/ })).not.toBeVisible()
  expect(creates(requests)).toHaveLength(0)
})
