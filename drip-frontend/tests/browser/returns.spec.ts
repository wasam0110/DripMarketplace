import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111'
const second = '22222222-2222-4222-8222-222222222222'
const token = 'private-return-test-code'
const detail = { id, order_id: second, seller_order_id: second, status: 'requested', reason: 'The fit was not right.', item_count: 1, requested_at: '2026-10-23T10:00:00Z', resolved_at: null, notes: 'Wait for instructions.', items: [{ id: second, order_item_id: second, quantity: 2, reason: null }] }
async function setup(page: Page, mode: 'normal' | 'empty' | 'denied' | 'malformed' | 'failed' | 'guest' = 'normal') {
  let signedIn = mode !== 'guest'
  const calls: { path: string; method: string; token?: string; authorization?: string }[] = []
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(signedIn ? { json: { access_token: 'fixture-token' } } : { status: 401, json: { error: { message: 'Guest' } } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'buyer', first_name: 'Buyer', role: 'customer', email: 'buyer@example.test' } })
    if (path.endsWith('/auth/logout')) { signedIn = false; return route.fulfill({ status: 204 }) }
    if (path.includes('/returns')) {
      calls.push({ path, method: req.method(), token: req.headers()['x-guest-token'], authorization: req.headers().authorization })
      if (mode === 'failed') return route.fulfill({ status: 503, json: { error: { message: 'Returns temporarily unavailable' } } })
      if (mode === 'denied' || (path.includes('/guest/') && req.headers()['x-guest-token'] !== token)) return route.fulfill({ status: 404, json: { error: { message: 'Not found' } } })
      if (path.endsWith('/returns')) {
        const current = Number(url.searchParams.get('page'))
        return route.fulfill({ json: { data: mode === 'empty' ? [] : [{ ...detail, id: current === 2 ? second : id }], total: mode === 'empty' ? 0 : 11, page: current, total_pages: mode === 'empty' ? 1 : 2 } })
      }
      return route.fulfill({ json: { ...detail, id: mode === 'malformed' ? second : id } })
    }
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  return calls
}
test('account history paginates, opens details and refreshes status without writes', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto('/account')
  await page.getByRole('link', { name: 'View your return history' }).click()
  await page.getByRole('link', { name: `View return ${id}`, exact: true }).waitFor()
  await page.getByRole('button', { name: 'Next page' }).click()
  await expect(page.getByRole('link', { name: `View return ${second}`, exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Next page' })).toBeDisabled()
  await page.getByRole('button', { name: 'Previous page' }).click()
  await page.getByRole('link', { name: `View return ${id}`, exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Requested', exact: true })).toBeVisible()
  await expect(page.getByText('Quantity: 2')).toBeVisible()
  await page.route(`**/api/v1/returns/${id}`, (route) => route.fulfill({ json: { ...detail, status: 'approved' } }))
  await page.getByRole('button', { name: 'Refresh return status' }).click()
  await expect(page.getByRole('heading', { name: 'Approved', exact: true })).toBeVisible()
  expect(calls.every((call) => call.method === 'GET' && call.authorization === 'Bearer fixture-token' && !call.token)).toBe(true)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('return-status.png'), fullPage: true })
})
test('guest status uses only a private header and forgets access on reload', async ({ page }, info) => {
  const calls = await setup(page, 'guest')
  await page.goto('/track-return')
  await page.getByLabel('Return reference').fill(id)
  await page.getByLabel('Private guest access code').fill(token)
  await page.getByRole('button', { name: 'View guest return' }).click()
  await expect(page.getByText('The fit was not right.')).toBeVisible()
  expect(calls[0]).toMatchObject({ path: `/api/v1/returns/guest/${id}`, method: 'GET', token })
  expect(calls[0].authorization).toBeUndefined()
  expect(page.url()).not.toContain(token)
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage }, state: history.state }))).not.toContain(token)
  await page.screenshot({ path: info.outputPath('guest-return-status.png'), fullPage: true })
  await page.reload()
  await expect(page.getByLabel('Private guest access code')).toHaveValue('')
  await expect(page.getByText('The fit was not right.')).not.toBeVisible()
})
for (const mode of ['denied', 'malformed', 'failed'] as const) test(`${mode} return detail hides private content and offers refresh`, async ({ page }) => {
  await setup(page, mode)
  await page.goto(`/returns/${id}`)
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByText('The fit was not right.')).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'Refresh return status' })).toBeEnabled()
})
test('empty history has no invented requests', async ({ page }) => {
  await setup(page, 'empty'); await page.goto('/returns')
  await expect(page.getByText('No return requests yet.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Next page' })).toBeDisabled()
})
test('guest cannot read account history or malformed references', async ({ page }) => {
  const calls = await setup(page, 'guest')
  await page.goto('/returns')
  await expect(page.getByRole('link', { name: 'Sign in', exact: true })).toBeVisible()
  await page.goto('/returns/not-a-reference')
  await expect(page.getByRole('heading', { name: 'Return unavailable' })).toBeVisible()
  expect(calls).toHaveLength(0)
})
test('wrong guest code denies details and permits changing credentials', async ({ page }) => {
  await setup(page, 'guest'); await page.goto('/track-return')
  await page.getByLabel('Return reference').fill(id)
  await page.getByLabel('Private guest access code').fill('wrong-code')
  await page.getByRole('button', { name: 'View guest return' }).click()
  await expect(page.getByRole('alert')).toContainText('unavailable with your current access')
  await expect(page.getByText('The fit was not right.')).not.toBeVisible()
  await page.getByRole('button', { name: 'Use different guest details' }).click()
  await expect(page.getByLabel('Private guest access code')).toHaveValue('')
})
