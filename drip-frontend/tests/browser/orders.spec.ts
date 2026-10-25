import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const id = '11111111-1111-4111-8111-111111111111'
const id2 = '22222222-2222-4222-8222-222222222222'
const token = 'private-guest-test-token'
async function reviewReturn(page: Page) {
  await page.getByRole('button', { name: 'Preview a return' }).click()
  await page.getByRole('checkbox', { name: /Linen overshirt/ }).check()
  await page.getByLabel('Reason for your return draft').fill('The fit was not right.')
  await page.getByRole('button', { name: 'Review draft' }).click()
}
for (const account of [true, false]) test(`return submission uses ${account ? 'account' : 'guest'} access`, async ({ page }, info) => {
  const calls = await setup(page, { account, returns: 'success', status: 'delivered' })
  await page.goto(account ? `/orders/${id}` : '/track')
  if (!account) {
    await page.getByLabel('Order number or ID').fill('WHZ-TEST-1')
    await page.getByLabel('Private guest access code').fill(token)
    await page.getByRole('button', { name: 'View guest order' }).click()
  }
  await reviewReturn(page)
  expect(calls.filter((call) => call.path.includes('/returns'))).toHaveLength(0)
  await page.getByRole('button', { name: 'Confirm return request' }).dblclick()
  await expect(page.getByRole('heading', { name: 'Return requested' })).toBeVisible()
  const writes = calls.filter((call) => call.path.includes('/returns'))
  expect(writes).toHaveLength(1)
  expect(writes[0].path).toBe(account ? '/api/v1/returns' : '/api/v1/returns/guest')
  expect(writes[0].authorization).toBe(account ? 'Bearer account-token' : undefined)
  expect(writes[0].token).toBe(account ? undefined : token)
  expect(JSON.parse(writes[0].body!)).toEqual({ seller_order_id: id, reason: 'The fit was not right.', items: [{ order_item_id: id, quantity: 1 }] })
  await page.screenshot({ path: info.outputPath('return-confirmed.png'), fullPage: true })
  await reviewReturn(page)
  await expect(page.getByRole('button', { name: 'Confirm return request' })).toBeDisabled()
})
for (const result of ['unknown', 'malformed'] as const) test(`${result} return outcome locks writes across order refresh`, async ({ page }) => {
  const calls = await setup(page, { account: true, returns: result, status: 'delivered' })
  await page.goto(`/orders/${id}`)
  await reviewReturn(page)
  await page.getByRole('button', { name: 'Confirm return request' }).click()
  await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.getByRole('button', { name: 'Refresh order status' }).click()
  await reviewReturn(page)
  await expect(page.getByRole('button', { name: 'Confirm return request' })).toBeDisabled()
  expect(calls.filter((call) => call.path.includes('/returns'))).toHaveLength(1)
})
test('return validation prevents mixed brands and displays prior-quantity rejection', async ({ page }) => {
  const calls = await setup(page, { account: true, returns: 'rejected', status: 'completed' })
  await page.goto(`/orders/${id}`)
  await page.getByRole('button', { name: 'Preview a return' }).click()
  await page.getByRole('checkbox', { name: /Linen overshirt/ }).check()
  await page.getByRole('checkbox', { name: /Cotton tee/ }).check()
  await page.getByLabel('Reason for your return draft').fill('The fit was not right.')
  await page.getByRole('button', { name: 'Review draft' }).click()
  await expect(page.getByRole('alert')).toContainText('one brand only')
  expect(calls.filter((call) => call.path.includes('/returns'))).toHaveLength(0)
  await page.getByRole('checkbox', { name: /Cotton tee/ }).uncheck()
  await page.getByRole('button', { name: 'Review draft' }).click()
  await page.getByRole('button', { name: 'Confirm return request' }).click()
  await expect(page.getByRole('alert')).toContainText('Cannot return more')
  await expect(page.getByRole('heading', { name: 'Return requested' })).not.toBeVisible()
})
async function reviewCancellation(page: Page) {
  await page.getByRole('button', { name: 'Preview cancellation' }).click()
  await page.getByLabel('Reason for your cancellation draft').fill('Changed my mind')
  await page.getByRole('button', { name: 'Review draft' }).click()
}

for (const account of [true, false]) test(`explicit cancellation uses ${account ? 'account' : 'guest'} access`, async ({ page }, info) => {
  const calls = await setup(page, { account, cancellation: 'success' })
  await page.goto(account ? `/orders/${id}` : '/track')
  if (!account) {
    await page.getByLabel('Order number or ID').fill('WHZ-TEST-1')
    await page.getByLabel('Private guest access code').fill(token)
    await page.getByRole('button', { name: 'View guest order' }).click()
  }
  await reviewCancellation(page)
  expect(calls.filter((call) => call.path.endsWith('/cancel'))).toHaveLength(0)
  await page.screenshot({ path: info.outputPath('cancellation-confirmation.png'), fullPage: true })
  await page.getByRole('button', { name: 'Yes, cancel the whole order' }).click()
  await expect(page.getByText('Order cancellation confirmed.', { exact: false })).toBeVisible()
  const writes = calls.filter((call) => call.path.endsWith('/cancel'))
  expect(writes).toHaveLength(1)
  expect(writes[0]).toMatchObject({ path: `/api/v1/orders/${id}/cancel`, method: 'POST', body: JSON.stringify({ reason: 'Changed my mind' }) })
  expect(writes[0].authorization).toBe(account ? 'Bearer account-token' : undefined)
  expect(writes[0].token).toBe(account ? undefined : token)
  await reviewCancellation(page)
  await expect(page.getByRole('button', { name: 'Yes, cancel the whole order' })).toBeDisabled()
})

test('uncertain cancellation stays locked after refreshing order data', async ({ page }) => {
  const calls = await setup(page, { account: true, cancellation: 'unknown' })
  await page.goto(`/orders/${id}`)
  await reviewCancellation(page)
  await page.getByRole('button', { name: 'Yes, cancel the whole order' }).click()
  await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.getByRole('button', { name: 'Refresh order status' }).click()
  await reviewCancellation(page)
  await expect(page.getByRole('button', { name: 'Yes, cancel the whole order' })).toBeDisabled()
  expect(calls.filter((call) => call.path.endsWith('/cancel'))).toHaveLength(1)
})

test('paid-order rejection is shown without claiming cancellation', async ({ page }) => {
  await setup(page, { account: true, cancellation: 'paid' })
  await page.goto(`/orders/${id}`)
  await reviewCancellation(page)
  await page.getByRole('button', { name: 'Yes, cancel the whole order' }).click()
  await expect(page.getByRole('alert')).toContainText('Contact support')
  await expect(page.getByText(/Order cancellation confirmed/)).not.toBeVisible()
})

test('dispatched shipments prevent cancellation submission', async ({ page }) => {
  const calls = await setup(page, { account: true })
  await page.goto(`/orders/${id}`)
  await reviewCancellation(page)
  await expect(page.getByRole('button', { name: 'Yes, cancel the whole order' })).toBeDisabled()
  expect(calls.filter((call) => call.path.endsWith('/cancel'))).toHaveLength(0)
})
const detail = {
  id, order_number: 'WHZ-TEST-1', status: 'processing', payment_method: 'cod', created_at: '2026-10-21T01:00:00Z',
  subtotal: '4500', discount_amount: '0', shipping_fee: '250', total: '4750', notes: null,
  address: { recipient_name: 'Test Customer', phone: '03001234567', street: '42 Private Street', city: 'Karachi', province: 'Sindh', note: 'Call on arrival' },
  items: [{ id: 'item-1', seller_id: 'seller-1', product_id: id, variant_id: id, product_name: 'Linen overshirt', variant_label: 'M / Ivory', quantity: 1, unit_price: '3000', subtotal: '3000' },
    { id: 'item-2', seller_id: 'seller-2', product_id: id2, variant_id: id2, product_name: 'Cotton tee', variant_label: 'S / Black', quantity: 1, unit_price: '1500', subtotal: '1500' }],
  seller_orders: [{ id: 'shipment-1', seller_id: 'seller-1', brand_name: 'Studio Label', status: 'shipped', subtotal: '3000', tracking_number: 'TRACK-123', courier_name: 'Test Courier', shipped_at: '2026-10-22T01:00:00Z', delivered_at: null },
    { id: 'shipment-2', seller_id: 'seller-2', brand_name: 'Second Label', status: 'processing', subtotal: '1500', tracking_number: null, courier_name: null, shipped_at: null, delivered_at: null }],
}
async function setup(page: Page, options: { account?: boolean; empty?: boolean; deny?: boolean; fail?: boolean; delay?: boolean; status?: string; cancellation?: 'success' | 'unknown' | 'paid'; returns?: 'success' | 'unknown' | 'rejected' | 'malformed' } = {}) {
  let signedIn = Boolean(options.account)
  let cancelled = false
  const calls: { path: string; method: string; token?: string; authorization?: string; body: string | null }[] = []
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    calls.push({ path, method: request.method(), token: request.headers()['x-guest-token'], authorization: request.headers().authorization, body: request.postData() })
    if (path.endsWith('/auth/refresh')) return route.fulfill(signedIn ? { json: { access_token: 'account-token' } } : { status: 401, json: { error: { message: 'Guest' } } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'account-1', email: 'buyer@example.test', role: 'customer', has_verified_email: true } })
    if (path.endsWith('/auth/logout')) { signedIn = false; return route.fulfill({ status: 204 }) }
    if (path.endsWith('/cart')) return route.fulfill({ json: { items: [], item_count: 0, subtotal: '0', shipping_fee: '0', total: '0' } })
    if ((path.endsWith('/returns') || path.endsWith('/returns/guest')) && request.method() === 'POST') {
      if (options.returns === 'unknown') return route.abort()
      if (options.returns === 'rejected') return route.fulfill({ status: 400, json: { error: { message: 'Cannot return more than purchased quantity' } } })
      const payload = request.postDataJSON()
      return route.fulfill({ status: 201, json: { ...payload, id: id2, order_id: options.returns === 'malformed' ? id2 : id, status: 'requested' } })
    }
    if (path.endsWith('/cancel')) {
      if (options.cancellation === 'unknown') return route.abort()
      if (options.cancellation === 'paid') return route.fulfill({ status: 400, json: { error: { message: 'Contact support to cancel and refund a paid order' } } })
      cancelled = true
      return route.fulfill({ json: { message: 'Order cancelled. Inventory has been released.' } })
    }
    if (path.endsWith('/reviews') && request.method() === 'POST') return route.fulfill({ status: 201, json: { id: id2, product_id: request.postDataJSON().product_id, status: 'pending', is_verified_purchase: true } })
    if (path.endsWith('/orders')) {
      if (options.fail) return route.fulfill({ status: 503, json: { error: { message: 'Orders temporarily unavailable' } } })
      const current = Number(url.searchParams.get('page'))
      return route.fulfill({ json: { data: options.empty ? [] : [{ id: current === 2 ? id2 : id, order_number: current === 2 ? 'WHZ-TEST-2' : 'WHZ-TEST-1', status: 'processing', total: '4750', item_count: 2, created_at: detail.created_at }], pagination: { page: current, per_page: 10, total: options.empty ? 0 : 11, total_pages: options.empty ? 1 : 2 } } })
    }
    if (path.includes('/orders/')) {
      if (options.delay) await new Promise((resolve) => setTimeout(resolve, 700))
      if (options.deny || (!signedIn && request.headers()['x-guest-token'] !== token)) return route.fulfill({ status: 404, json: { error: { message: 'Not found' } } })
      return route.fulfill({ json: { ...detail, status: cancelled ? 'cancelled' : options.status ?? detail.status,
        items: detail.items.map((item, index) => ({ ...item, id: index ? id2 : id })),
        seller_orders: detail.seller_orders.map((shipment, index) => ({ ...shipment, id: index ? id2 : id, status: options.cancellation ? cancelled ? 'cancelled' : 'processing' : shipment.status })) } })
    }
    return route.fulfill({ status: 500, json: { error: { message: 'Unexpected request' } } })
  })
  return calls
}

test('account order history paginates and shows per-brand tracking', async ({ page }, info) => {
  const calls = await setup(page, { account: true })
  await page.goto('/orders')
  await expect(page.getByRole('link', { name: 'View order WHZ-TEST-1' })).toBeVisible()
  await page.getByRole('button', { name: 'Next page' }).click()
  await expect(page.getByRole('link', { name: 'View order WHZ-TEST-2' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Next page' })).toBeDisabled()
  await page.getByRole('button', { name: 'Previous page' }).click()
  await page.getByRole('link', { name: 'View order WHZ-TEST-1' }).click()
  await expect(page.getByRole('heading', { name: 'Order WHZ-TEST-1' })).toBeVisible()
  const shipments = page.locator('.shipment-card')
  await expect(shipments.nth(0)).toContainText('Shipped')
  await expect(shipments.nth(0)).toContainText('TRACK-123')
  await expect(shipments.nth(1)).toContainText('Preparing your order')
  await expect(shipments.nth(1)).toContainText('Not available yet')
  await expect(page.locator('address')).toContainText('42 Private Street')
  expect(calls.filter((call) => call.path.includes('/orders')).every((call) => call.method === 'GET' && call.authorization === 'Bearer account-token')).toBe(true)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('order-detail.png'), fullPage: true })
})
test('guest access sends the private code only in a header and forgets it on reload', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/track')
  await page.getByLabel('Order number or ID').fill('WHZ-TEST-1')
  await page.getByLabel('Private guest access code').fill(token)
  await page.getByRole('button', { name: 'View guest order' }).click()
  await expect(page.getByRole('heading', { name: 'Order WHZ-TEST-1' })).toBeVisible()
  const read = calls.find((call) => call.path.endsWith('/orders/number/WHZ-TEST-1'))
  expect(read?.token).toBe(token)
  expect(read?.authorization).toBeUndefined()
  expect(read?.body).toBeNull()
  expect(page.url()).not.toContain(token)
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage }, history: history.state }))).not.toContain(token)
  await page.reload()
  await expect(page.getByLabel('Private guest access code')).toHaveValue('')
  await expect(page.locator('address')).not.toBeVisible()
})
test('guests cannot enumerate account history or read details from an ID alone', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/orders')
  await expect(page.getByRole('link', { name: 'Sign in', exact: true })).toBeVisible()
  await page.goto(`/orders/${id}`)
  await expect(page.getByLabel('Private guest access code')).toBeVisible()
  expect(calls.filter((call) => call.path.includes('/orders'))).toHaveLength(0)
})
test('denied order access never shows private delivery data', async ({ page }) => {
  await setup(page, { account: true, deny: true })
  await page.goto(`/orders/${id}`)
  await expect(page.getByRole('alert')).toContainText('unavailable with your current access')
  await expect(page.locator('address')).not.toBeVisible()
  await expect(page.getByText('42 Private Street')).not.toBeVisible()
})
test('history handles empty and failed states without invented orders', async ({ page }) => {
  await setup(page, { account: true, empty: true })
  await page.goto('/orders')
  await expect(page.getByRole('heading', { name: 'Your first order starts here.' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Next page' })).toBeDisabled()
  await page.unroute('**/api/v1/**')
  await setup(page, { account: true, fail: true })
  await page.reload()
  await expect(page.getByRole('alert')).toContainText('temporarily unavailable')
  await expect(page.locator('.order-card')).toHaveCount(0)
})
test('signing out removes protected order views', async ({ page }) => {
  await setup(page, { account: true })
  await page.goto(`/orders/${id}`)
  await expect(page.locator('address')).toBeVisible()
  await page.getByRole('link', { name: 'My account', exact: true }).first().click()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Let’s get you back in.' })).toBeVisible()
  await page.goBack()
  await expect(page.getByLabel('Private guest access code')).toBeVisible()
  await expect(page.locator('address')).not.toBeVisible()
})

test('return draft supports item selection and review without writes or saved details', async ({ page }, info) => {
  const calls = await setup(page, { account: true, status: 'delivered' })
  await page.goto(`/orders/${id}`)
  await page.getByRole('button', { name: 'Preview a return' }).click()
  await page.getByRole('checkbox', { name: /Linen overshirt/ }).check()
  await page.getByLabel('Reason for your return draft').fill('The fit was not right.')
  await page.getByRole('button', { name: 'Review draft' }).click()
  await expect(page.getByRole('heading', { name: 'Review your draft' })).toBeFocused()
  await expect(page.getByRole('button', { name: 'Confirm return request' })).toBeEnabled()
  await expect(page.getByRole('region', { name: 'Cancellation and returns' })).toContainText('Submission is not approval or a refund')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('region', { name: 'Cancellation and returns' }).screenshot({ path: info.outputPath('return-draft.png') })
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))).not.toContain('The fit was not right.')
  expect(calls.filter((call) => call.path.includes('/returns') && call.method !== 'GET')).toHaveLength(0)
  await page.reload()
  await page.getByRole('button', { name: 'Preview a return' }).click()
  await expect(page.getByLabel('Reason for your return draft')).toHaveValue('')
  await expect(page.getByRole('checkbox', { name: /Linen overshirt/ })).not.toBeChecked()
})

test('guest cancellation is clearly an unsent draft and can be discarded', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/track')
  await page.getByLabel('Order number or ID').fill('WHZ-TEST-1')
  await page.getByLabel('Private guest access code').fill(token)
  await page.getByRole('button', { name: 'View guest order' }).click()
  await page.getByRole('button', { name: 'Preview cancellation' }).click()
  await page.getByLabel('Reason for your cancellation draft').fill('Ordered by mistake')
  await page.getByRole('button', { name: 'Review draft' }).click()
  await expect(page.getByRole('button', { name: 'Yes, cancel the whole order' })).toBeDisabled()
  await page.getByRole('button', { name: 'Discard draft' }).click()
  await expect(page.getByRole('button', { name: 'Preview cancellation' })).toBeFocused()
  expect(calls.filter((call) => call.path.includes('/orders') && call.method !== 'GET')).toHaveLength(0)
})

test('delivered account order links each review to the order without claiming publication', async ({ page }, info) => {
  const calls = await setup(page, { account: true, status: 'delivered' })
  await page.goto(`/orders/${id}`)
  const section = page.getByRole('region', { name: 'Review your pieces' })
  await section.getByRole('button', { name: 'Review Linen overshirt', exact: true }).click()
  await section.getByRole('button', { name: 'Review Cotton tee', exact: true }).click()
  const forms = section.locator('form')
  await expect(forms).toHaveCount(2)
  await forms.nth(0).getByRole('combobox', { name: 'Rating', exact: true }).selectOption('5')
  await forms.nth(0).getByLabel('Your review (optional)', { exact: true }).fill('Great fit.')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('order-reviews.png'), fullPage: true })
  await forms.nth(0).getByRole('button', { name: 'Submit review' }).click()
  await expect(section.getByText('Review received and awaiting moderation.', { exact: false })).toBeVisible()
  const writes = calls.filter((call) => call.path.endsWith('/reviews'))
  expect(writes).toHaveLength(1)
  expect(JSON.parse(writes[0].body!)).toEqual({ product_id: id, order_id: id, rating: 5, title: null, body: 'Great fit.' })
  expect(writes[0].authorization).toBe('Bearer account-token')
  expect(writes[0].token).toBeUndefined()
  await expect(section.locator('form')).toHaveCount(1)
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain('Great fit.')
})

test('processing account orders do not offer purchase-linked reviews', async ({ page }) => {
  await setup(page, { account: true })
  await page.goto(`/orders/${id}`)
  await expect(page.getByRole('heading', { name: 'Order WHZ-TEST-1' })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Review your pieces' })).toHaveCount(0)
})

test('delivered guest orders do not offer account purchase-linked reviews', async ({ page }) => {
  await setup(page, { status: 'delivered' })
  await page.goto('/track')
  await page.getByLabel('Order number or ID').fill('WHZ-TEST-1')
  await page.getByLabel('Private guest access code').fill(token)
  await page.getByRole('button', { name: 'View guest order' }).click()
  await expect(page.getByRole('heading', { name: 'Order WHZ-TEST-1' })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Review your pieces' })).toHaveCount(0)
})
