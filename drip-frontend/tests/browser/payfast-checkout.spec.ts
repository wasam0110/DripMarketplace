import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
test.skip(process.env.VITE_ENABLE_PAYFAST !== 'true', 'Run the isolated opt-in PayFast test command; default builds keep handoff disabled.')
const id = '33333333-3333-4333-8333-333333333333'
const attemptId = '55555555-5555-4555-8555-555555555555'
const item = { product_id: '11111111-1111-4111-8111-111111111111', variant_id: '22222222-2222-4222-8222-222222222222', quantity: 1 }
const endpoint = 'https://ipguat.apps.net.pk/Ecommerce/api/Transaction/PostTransaction'
async function setup(page: Page, mode = 'normal', account = false) {
  const calls = { orders: 0, initiations: 0, provider: 0, methods: [] as string[] }
  const quote = { items: [{ ...item, product_name: 'Linen shirt', brand_name: 'Label', brand_color: '#203c32', primary_image: null, size: 'M', colour: 'Ivory', unit_price: '4500', subtotal: '4500', available_stock: 3, seller_id: 'seller' }], item_count: 1, subtotal: '4500', discount_amount: '0', shipping_fee: '250', total: '4750', currency: 'PKR', quote_expires_at: '2030-01-01T00:00:00Z', payment_methods: [{ method: 'cod', available: true, unavailable_reason: null }, { method: 'payfast', available: mode !== 'disabled', unavailable_reason: null }] }
  const order = { order_id: id, order_number: 'WHZ-PF', status: 'pending_payment', total: '4750', payment_method: 'payfast', guest_token: account ? null : 'private-guest-code', whatsapp_url: null }
  await page.addInitScript((selection) => localStorage.setItem('wearhowz.guest-bag.v1', JSON.stringify([selection])), item)
  await page.route(endpoint, (route) => {
    calls.provider++
    expect(route.request().method()).toBe('POST')
    const data = new URLSearchParams(route.request().postData()!)
    expect(data.get('BASKET_ID')).toBe(attemptId); expect(data.get('TXNAMT')).toBe('4750.00')
    expect(route.request().postData()).not.toContain('private-guest-code')
    return route.fulfill({ contentType: 'text/html', body: '<h1>Mock PayFast handoff received</h1>' })
  })
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(account ? { json: { access_token: 'fixture' } } : { status: 401, json: {} })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'account', email: 'buyer@example.test', role: 'customer' } })
    if (path.endsWith('/cart')) return route.fulfill({ json: quote })
    if (path.endsWith('/me/addresses')) return route.fulfill({ json: [] })
    if (path.endsWith('/quote')) {
      const body = req.postDataJSON(); calls.methods.push(body.payment_method)
      return route.fulfill({ json: { ...quote, quote_token: `signed-${body.payment_method}` } })
    }
    if (path.endsWith('/recover')) return route.fulfill({ json: order })
    if (path === '/api/v1/orders' || path === '/api/v1/orders/guest') {
      calls.orders++
      expect(req.postDataJSON().payment_method).toBe('payfast')
      expect(req.postDataJSON().quote_token).toBe('signed-payfast')
      return route.fulfill({ status: 201, json: order })
    }
    if (path.endsWith('/payments/initiate')) {
      calls.initiations++
      expect(req.postDataJSON()).toEqual({ order_id: id })
      expect(req.headers()[account ? 'authorization' : 'x-guest-token']).toBe(account ? 'Bearer fixture' : 'private-guest-code')
      if (mode === 'lost') return route.abort()
      const origin = 'http://127.0.0.1:3000'
      return route.fulfill({ json: { payment_id: id, attempt_id: attemptId, method: 'payfast', checkout_url: mode === 'unsafe' ? 'https://evil.example.test' : endpoint, payfast_payload: {
        MERCHANT_ID: 'fixture', MERCHANT_NAME: 'WearHowZ', TOKEN: 'private-provider-token', PROCCODE: '00', TXNAMT: '4750.00', CUSTOMER_MOBILE_NO: '03001234567', CUSTOMER_EMAIL_ADDRESS: 'buyer@example.test', SIGNATURE: 'fixture', VERSION: 'WHZ-1.0', TXNDESC: 'Order', SUCCESS_URL: `${origin}/order/success/${id}`, FAILURE_URL: `${origin}/payments/${id}?payment=failed`, BASKET_ID: attemptId, ORDER_DATE: '2026-10-24', CHECKOUT_URL: `${origin}/api/v1/payments/callback/payfast`, CURRENCY_CODE: 'PKR',
      } } })
    }
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  await page.goto('/checkout')
  return calls
}
async function create(page: Page, account = false) {
  if (!account) await page.getByLabel('Email address', { exact: true }).fill('guest@example.test')
  await page.getByLabel('Recipient name').fill('Test Customer')
  await page.getByLabel('Mobile number').fill('03001234567')
  await page.getByLabel('Street address', { exact: true }).fill('42 Test Street')
  await page.getByLabel('City', { exact: true }).fill('Karachi')
  await page.getByLabel('Province', { exact: true }).selectOption('Sindh')
  await page.getByRole('button', { name: 'Continue to payment' }).click()
  // Method changes intentionally replace the radio while loading a fresh signed quote.
  await page.getByRole('radio', { name: /Pay online/ }).click()
  await expect(page.getByRole('heading', { name: 'Where should we send it?' })).toBeVisible()
  await page.getByRole('button', { name: 'Continue to payment' }).click()
  await page.getByRole('radio', { name: /Pay online/ }).check()
  await page.getByRole('button', { name: 'Review your order' }).click()
  await page.getByRole('button', { name: /Place order/ }).click()
  await expect(page.getByRole('heading', { name: 'Your order: WHZ-PF' })).toBeVisible()
}
for (const account of [false, true]) test(`${account ? 'account' : 'guest'} uses a fresh quote and explicit provider POST`, async ({ page }, info) => {
  const calls = await setup(page, 'normal', account)
  await create(page, account)
  expect(calls.methods).toContain('payfast'); expect(calls.orders).toBe(1)
  expect(calls.initiations).toBe(0); expect(calls.provider).toBe(0)
  if (!account) {
    await expect(page.getByRole('button', { name: 'Prepare PayFast payment' })).toBeDisabled()
    await page.getByRole('checkbox', { name: /I have saved this private code/ }).check()
  }
  await page.getByRole('button', { name: 'Prepare PayFast payment' }).click()
  await expect(page.getByRole('button', { name: 'Continue to PayFast', exact: true })).toBeVisible()
  expect(calls.initiations).toBe(1); expect(calls.provider).toBe(0)
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toMatch(/private-provider-token|private-guest-code|Test Street/)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.screenshot({ path: info.outputPath('payfast-handoff.png'), fullPage: true })
  await page.getByRole('button', { name: 'Continue to PayFast', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Mock PayFast handoff received' })).toBeVisible()
  expect(calls.provider).toBe(1)
})
for (const mode of ['lost', 'unsafe']) test(`${mode} initiation locks retries across checkout recovery`, async ({ page }) => {
  const calls = await setup(page, mode, true)
  await create(page, true)
  await page.getByRole('button', { name: 'Prepare PayFast payment' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Continue to PayFast', exact: true })).toHaveCount(0)
  await page.reload()
  await page.getByRole('button', { name: 'Check order status', exact: true }).click()
  await expect(page.getByText(/A new payment attempt is locked/)).toBeVisible()
  expect(calls.initiations).toBe(1); expect(calls.orders).toBe(1); expect(calls.provider).toBe(0)
})
test('server availability still gates the opt-in frontend', async ({ page }) => {
  await setup(page, 'disabled', true)
  await page.getByLabel('Recipient name').fill('Test Customer')
  await page.getByLabel('Mobile number').fill('03001234567')
  await page.getByLabel('Street address', { exact: true }).fill('42 Test Street')
  await page.getByLabel('City', { exact: true }).fill('Karachi')
  await page.getByLabel('Province', { exact: true }).selectOption('Sindh')
  await page.getByRole('button', { name: 'Continue to payment' }).click()
  await expect(page.getByRole('radio', { name: /Pay online/ })).toBeDisabled()
})
