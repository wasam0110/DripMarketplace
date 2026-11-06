import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

async function fixture(page: Page, mode: 'paid' | 'free' | 'lost' | 'changed' | 'rejected' | 'malformed' = 'paid', role?: string) {
  const submissions: Record<string, unknown>[] = []
  const unexpected: string[] = []
  let changed = false
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(role ? { json: { access_token: 'fixture-token' } } : { status: 401, json: { error: { message: 'No session' } } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, email: 'owner@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: true } })
    if (path.endsWith('/cart')) return route.fulfill({ json: { items: [], item_count: 0, subtotal: '0', shipping_fee: '0', total: '0' } })
    if (path.endsWith('/seller/register/slot-price')) {
      const extra = Number(new URL(route.request().url()).searchParams.get('extra_slots'))
      const fee = mode === 'free' ? 0 : mode === 'changed' && changed ? 6000 : 5000
      return route.fulfill({ json: { registration_fee: fee.toFixed(2), base_slots: 50, extra_slots: extra,
        extra_slot_price: '50.00', extra_cost: (extra * 50).toFixed(2), total_cost: (fee + extra * 50).toFixed(2), total_slots: 50 + extra } })
    }
    if (path.endsWith('/seller/register') && route.request().method() === 'POST') {
      submissions.push(route.request().postDataJSON())
      if (mode === 'lost') return route.abort()
      if (mode === 'rejected') return route.fulfill({ status: 422, json: { error: { message: 'Please correct your brand details', fields: { brand_name: 'Brand name is invalid' } } } })
      if (mode === 'malformed') return route.fulfill({ json: { message: 'Unconfirmed' } })
      await new Promise((resolve) => setTimeout(resolve, 150))
      return route.fulfill({ status: 201, json: { seller_id: '11111111-1111-4111-8111-111111111111', amount_due: mode === 'free' ? '0.00' : '5100.00', message: 'Application submitted for review.' } })
    }
    unexpected.push(`${route.request().method()} ${path}`)
    return route.fulfill({ status: 404, json: { error: { message: 'Unexpected request' } } })
  })
  return { submissions, unexpected, changePrice: () => { changed = true } }
}
async function fill(page: Page, extra = '2') {
  await page.getByLabel('First name', { exact: true }).fill('Ayesha')
  await page.getByLabel('Email address', { exact: true }).fill('seller@example.test')
  await page.getByLabel('Password', { exact: true }).fill('Fixture123')
  await page.getByLabel('Brand name', { exact: true }).fill('Fixture Label')
  await page.getByLabel('Brand description', { exact: true }).fill('Independent cotton clothing.')
  await page.getByLabel('Return policy', { exact: true }).fill('Contact our label to request a return.')
  await page.getByLabel('WhatsApp mobile number', { exact: true }).fill('03001234567')
  await page.getByLabel('Extra listing slots', { exact: true }).fill(extra)
  await expect(page.getByRole('button', { name: 'Review application', exact: true })).toBeEnabled()
  await page.getByRole('button', { name: 'Review application', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Review your application', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Review your application', exact: true })).toBeFocused()
}

for (const mode of ['paid', 'free'] as const) test(`${mode} registration requires review and submits once`, async ({ page }, info) => {
  const state = await fixture(page, mode)
  await page.goto('/seller/register')
  await fill(page, mode === 'free' ? '0' : '2')
  expect(state.submissions).toHaveLength(0)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  // Capture from the top so off-viewport fixed controls stay outside the screenshot.
  await page.getByRole('heading', { name: 'Review your application', exact: true }).focus()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('seller-registration-review.png'), fullPage: true })
  await page.getByRole('button', { name: 'Submit seller application', exact: true }).dblclick()
  await expect(page.getByRole('heading', { name: 'Application received', exact: true })).toBeVisible()
  expect(state.submissions).toHaveLength(1)
  expect(state.submissions[0]).toEqual({ first_name: 'Ayesha', last_name: null, email: 'seller@example.test', password: 'Fixture123', brand_name: 'Fixture Label', description: 'Independent cotton clothing.', return_policy: 'Contact our label to request a return.', whatsapp_number: '03001234567', instagram_handle: null, extra_slots: mode === 'free' ? 0 : 2 })
  expect(state.unexpected).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  const saved = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))
  for (const secret of ['Fixture123', 'seller@example.test', 'Fixture Label', '03001234567']) expect(saved).not.toContain(secret)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Check an existing application first' })).toBeVisible()
  expect(state.submissions).toHaveLength(1)
})

for (const mode of ['lost', 'malformed'] as const) test(`${mode} response blocks replay across reload`, async ({ page }) => {
  const state = await fixture(page, mode)
  await page.goto('/seller/register'); await fill(page)
  await page.getByRole('button', { name: 'Submit seller application', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Check an existing application first' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Application received' })).toHaveCount(0)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Check an existing application first' })).toBeVisible()
  expect(state.submissions).toHaveLength(1)
})

test('changed pricing requires another review without submitting', async ({ page }) => {
  const state = await fixture(page, 'changed')
  await page.goto('/seller/register'); await fill(page)
  state.changePrice()
  await page.getByRole('button', { name: 'Submit seller application', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Pricing changed')
  expect(state.submissions).toHaveLength(0)
  await expect(page.getByRole('button', { name: 'Review application', exact: true })).toBeEnabled()
})

test('validation rejection permits editing but never automatically retries', async ({ page }) => {
  const state = await fixture(page, 'rejected')
  await page.goto('/seller/register'); await fill(page)
  await page.getByRole('button', { name: 'Submit seller application', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Please correct')
  await expect(page.getByLabel('Brand name', { exact: true })).toBeEnabled()
  await expect(page.getByLabel('Password', { exact: true })).toHaveValue('')
  expect(state.submissions).toHaveLength(1)
  expect(await page.evaluate(() => sessionStorage.getItem('wearhowz:seller-registration-submitted:v1'))).toBeNull()
})

test('storage failure blocks registration', async ({ page }) => {
  const state = await fixture(page)
  await page.addInitScript(() => { Storage.prototype.setItem = () => { throw new Error('Storage unavailable') } })
  await page.goto('/seller/register'); await fill(page)
  await page.getByRole('button', { name: 'Submit seller application', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Storage unavailable')
  expect(state.submissions).toHaveLength(0)
})

for (const role of ['seller', 'customer', 'admin']) test(`${role} cannot create another account while signed in`, async ({ page }) => {
  const state = await fixture(page, 'paid', role)
  await page.goto('/seller/register')
  await expect(page.getByRole('heading', { name: 'You are already signed in' })).toBeVisible()
  await expect(page.getByLabel('Password', { exact: true })).toHaveCount(0)
  expect(state.submissions).toHaveLength(0)
})

test('unavailable pricing blocks review and submission', async ({ page }) => {
  const state = await fixture(page)
  await page.route('**/seller/register/slot-price?*', (route) => route.fulfill({ status: 503, json: { error: { message: 'Pricing unavailable' } } }))
  await page.goto('/seller/register')
  await expect(page.getByRole('alert')).toContainText('Pricing unavailable')
  await expect(page.getByRole('button', { name: 'Review application', exact: true })).toBeDisabled()
  expect(state.submissions).toHaveLength(0)
})
