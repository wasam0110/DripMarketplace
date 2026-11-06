import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const seller = '11111111-1111-4111-8111-111111111111', product = '22222222-2222-4222-8222-222222222222', shipment = '33333333-3333-4333-8333-333333333333'
async function setup(page: Page, mode = 'ready', role = 'seller', verified = true) {
  const reads: string[] = [], writes: string[] = []
  let denied = mode === 'denied'
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, email: 'seller@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.includes('/seller/')) {
      reads.push(`${path}${url.search}`)
      expect(route.request().headers().authorization).toBe('Bearer fixture-token')
      if (method !== 'GET') { writes.push(method); return route.fulfill({ status: 405 }) }
    }
    if (path.endsWith('/seller/me')) return route.fulfill({ json: { id: seller, brand_name: 'Fixture Label', status: mode === 'inactive' ? 'suspended' : 'active', registration_amount_due: '0.00', registration_paid_at: null } })
    if (path.includes('/seller/analytics/')) {
      if (denied) return route.fulfill({ status: 403, json: { error: { message: 'Analytics unavailable' } } })
      const period = url.searchParams.get('period') || '30d'
      if (mode === 'slow' && period === '7d') await new Promise((resolve) => setTimeout(resolve, 500))
      if (path.endsWith('/overview')) return route.fulfill({ json: { period: mode === 'mismatch' ? '90d' : period, gross_revenue: mode === 'malformed' ? 1000.2 : '1000.20', commission_paid: '150.03', net_earnings: '850.17', order_count: period === '7d' ? 7 : period === '90d' ? 90 : 1, units_sold: 2, avg_order_value: '1000.20', total_views: 10, conversion_rate: 10 } })
      if (path.endsWith('/revenue')) return route.fulfill({ json: { period, granularity: url.searchParams.get('granularity'), data: mode === 'empty' ? [] : [{ date: '2026-10-26', gross: '1000.20', commission: '150.03', net: '850.17', orders: 1 }] } })
      if (path.endsWith('/top-products')) return route.fulfill({ json: { period, sort_by: url.searchParams.get('sort_by'), data: mode === 'empty' ? [] : [{ product_id: product, product_name: 'Everyday linen coat', revenue: '1500.25', units_sold: 2, views: 50, avg_rating: 4.5, image_url: null }] } })
      if (path.endsWith('/inventory-health')) return route.fulfill({ json: { total_variants: 5, in_stock: 3, low_stock: 2, out_of_stock: 2, total_units: 8 } })
    }
    if (path.endsWith('/commission-breakdown')) {
      const p = Number(url.searchParams.get('page') || 1)
      const entry = { id: seller, seller_order_id: shipment, commission_rate: 0.15, settled_at: '2026-10-28T10:00:00Z', released_at: p === 1 ? null : '2026-10-28T12:00:00Z',
        gross_amount: '1000.20', commission_amount: '150.03', seller_amount: '850.17', original_gross_amount: '1500.25', original_commission_amount: '225.04', original_seller_amount: '1275.21',
        refunded_gross_amount: '500.05', reversed_commission_amount: '75.01', reversed_seller_amount: '425.04', recovered_seller_amount: '400', settlement_offset_amount: '25.04', platform_shortfall_amount: '0' }
      const summary = { total_gross: '1000.20', total_commission: '150.03', total_net: '850.17', original_gross: '1500.25', original_commission: '225.04', original_net: '1275.21', total_refunded_gross: '500.05', total_reversed_commission: '75.01', total_reversed_seller: mode === 'bad-ledger' ? '425.03' : '425.04', total_recovered_seller: '400', total_settlement_offset: '25.04', total_platform_shortfall: '0' }
      return route.fulfill({ json: { data: mode === 'empty' ? [] : [entry], summary, total: mode === 'empty' ? 0 : 26, page: p } })
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return { reads, writes, allow: () => { denied = false } }
}
test('shows exact earnings, scoped product metrics and stock health', async ({ page }, info) => {
  const state = await setup(page); await page.goto('/seller/analytics')
  await expect(page.getByRole('heading', { name: 'Sales overview', exact: true })).toBeVisible()
  await expect(page.getByText('PKR 850.17', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'Everyday linen coat' })).toHaveAttribute('href', `/seller/products/${product}/edit`)
  await expect(page.getByText(/Views and ratings are lifetime figures/)).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Current stock health' })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('seller-analytics.png'), fullPage: true }); expect(state.writes).toEqual([])
})
test('period, interval and ranking controls issue supported scoped reads', async ({ page }) => {
  const state = await setup(page); await page.goto('/seller/analytics'); await expect(page.getByText('PKR 850.17', { exact: true }).first()).toBeVisible()
  await page.getByLabel('Performance period', { exact: true }).selectOption('7d')
  await page.getByLabel('Group settlements by', { exact: true }).selectOption('week')
  await page.getByLabel('Rank products by', { exact: true }).selectOption('views')
  await expect(page.getByRole('link', { name: 'Everyday linen coat' })).toBeVisible()
  expect(state.reads).toContain('/api/v1/seller/analytics/overview?period=7d')
  expect(state.reads).toContain('/api/v1/seller/analytics/revenue?period=7d&granularity=week')
  expect(state.reads).toContain('/api/v1/seller/analytics/top-products?period=7d&sort_by=views&limit=10')
  expect(state.writes).toEqual([])
})
test('commission ledger distinguishes originals, reversals, recoveries and release records', async ({ page }, info) => {
  const state = await setup(page); await page.goto('/seller/analytics'); await page.getByRole('button', { name: 'Commission ledger', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'All-time commission ledger' })).toBeVisible()
  await expect(page.getByText('Page 1 of 2 · 26 entries', { exact: true })).toBeVisible()
  await expect(page.getByText('No release recorded', { exact: true })).toBeVisible()
  await page.getByText('All-time refund and recovery totals', { exact: true }).click()
  await page.getByText('Settlement refund details', { exact: true }).click()
  await expect(page.getByText('PKR 425.04', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('link', { name: `View brand shipment ${shipment}` })).toHaveAttribute('href', `/seller/orders/${shipment}`)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('seller-commission.png'), fullPage: true })
  await page.getByRole('button', { name: 'Next commission page', exact: true }).click()
  await expect(page.getByText('Page 2 of 2 · 26 entries', { exact: true })).toBeVisible()
  await expect(page.getByText(/^Release recorded/)).toBeVisible()
  expect(state.reads).toContain('/api/v1/seller/wallet/commission-breakdown?page=2')
  expect(state.reads.some((value) => value.includes('date_from') || value.includes('date_to'))).toBe(false)
  expect(state.writes).toEqual([])
})
test('empty results remain empty rather than invented zero-filled trends', async ({ page }) => {
  await setup(page, 'empty'); await page.goto('/seller/analytics'); await expect(page.getByText('No settlements in this period', { exact: true })).toBeVisible(); await expect(page.getByText('No products to rank', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Commission ledger', exact: true }).click(); await expect(page.getByText('No settlement entries on this page', { exact: true })).toBeVisible(); await expect(page.getByRole('button', { name: 'Next commission page', exact: true })).toBeDisabled()
})
test('denied analytics may be retried without losing independent sections', async ({ page }) => {
  const state = await setup(page, 'denied'); await page.goto('/seller/analytics'); await expect(page.getByText('Analytics unavailable', { exact: true }).first()).toBeVisible()
  state.allow(); await page.getByRole('button', { name: 'Refresh sales overview', exact: true }).click(); await expect(page.getByText('PKR 850.17', { exact: true }).first()).toBeVisible(); expect(state.writes).toEqual([])
})
for (const mode of ['malformed', 'mismatch']) test(`${mode} overview is rejected`, async ({ page }) => {
  await setup(page, mode); await page.goto('/seller/analytics'); await expect(page.getByText('The analytics information could not be verified. Refresh to try again.', { exact: true })).toBeVisible()
  await expect(page.getByText('Net earnings', { exact: true })).toHaveCount(0)
})
test('inconsistent commission summary is not rendered as earnings', async ({ page }) => {
  await setup(page, 'bad-ledger'); await page.goto('/seller/analytics'); await page.getByRole('button', { name: 'Commission ledger', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('could not be verified'); await expect(page.getByText('Net earnings', { exact: true })).toHaveCount(0)
})
test('late responses from an earlier period never replace the chosen period', async ({ page }) => {
  await setup(page, 'slow'); await page.goto('/seller/analytics'); await page.getByLabel('Performance period', { exact: true }).selectOption('7d'); await page.getByLabel('Performance period', { exact: true }).selectOption('90d')
  const metric = page.locator('.analytics-metrics div').filter({ has: page.locator('dt', { hasText: /^Settled brand shipments$/ }) })
  await expect(metric.locator('dd')).toHaveText('90'); await page.waitForTimeout(650); await expect(metric.locator('dd')).toHaveText('90')
})
for (const [role, verified, mode, heading] of [['guest', true, 'ready', 'Sign in to view seller analytics'], ['customer', true, 'ready', 'A seller account is required'], ['admin', true, 'ready', 'A seller account is required'], ['seller', false, 'ready', 'Verify your email first'], ['seller', true, 'inactive', 'An active seller account is required to view analytics.']] as const) test(`${role} verified=${verified} ${mode} is gated`, async ({ page }) => {
  const state = await setup(page, mode, role, verified); await page.goto('/seller/analytics'); await expect(page.getByText(heading, { exact: true })).toBeVisible(); expect(state.reads.filter((value) => !value.endsWith('/seller/me'))).toEqual([])
})
