import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111'
const owner = '22222222-2222-4222-8222-222222222222'
const other = '33333333-3333-4333-8333-333333333333'
const when = '2026-10-23T10:00:00Z'
const returned = { id, order_id: id, seller_order_id: id, status: 'rejected', reason: 'The fit was not right.', item_count: 1, requested_at: when, resolved_at: when, notes: null, items: [{ id, order_item_id: id, quantity: 1, reason: null }] }
const initial = { id, return_id: id, seller_id: other, status: 'open', created_at: when, resolved_at: null as string | null, resolution_note: null as string | null, messages: [{ id, sender_id: owner, body: 'Please reconsider this return.', created_at: when }] }
async function setup(page: Page, mode: 'missing' | 'existing' | 'resolved' | 'guest' | 'not-rejected' | 'denied' | 'malformed' | 'lost-open' | 'lost-message' | 'rejected-write' = 'missing') {
  let dispute = ['existing', 'resolved', 'lost-message', 'malformed'].includes(mode) ? structuredClone(initial) : null
  if (dispute && mode === 'resolved') { dispute.status = 'resolved_customer'; dispute.resolution_note = 'The return was reconsidered.'; dispute.resolved_at = when }
  const writes: { path: string; body: unknown; authorization?: string }[] = []
  const reads: string[] = []
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(mode === 'guest' ? { status: 401, json: { error: { message: 'Guest' } } } : { json: { access_token: 'dispute-test-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: owner, email: 'buyer@example.test', role: 'customer' } })
    if (path.includes('/returns')) {
      if (req.method() === 'GET') reads.push(path)
      else writes.push({ path, body: req.postDataJSON(), authorization: req.headers().authorization })
      if (path.endsWith(`/returns/${id}`)) return route.fulfill({ json: { ...returned, status: mode === 'not-rejected' ? 'approved' : 'rejected' } })
      if (mode === 'denied') return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: 'Return not found.' } } })
      if (req.method() === 'GET') return dispute ? route.fulfill({ json: { ...dispute, return_id: mode === 'malformed' ? other : id } }) : route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: 'No dispute found for this return not found.' } } })
      if (mode === 'rejected-write') return route.fulfill({ status: 400, json: { error: { message: 'A dispute is already open for this return' } } })
      if (path.endsWith('/messages')) {
        const message = { id: other, sender_id: owner, body: req.postDataJSON().body, created_at: when }
        dispute!.messages.push(message)
        if (mode === 'lost-message') return route.abort()
        return route.fulfill({ status: 201, json: message })
      }
      dispute = { ...structuredClone(initial), messages: [{ ...initial.messages[0], body: req.postDataJSON().message }] }
      if (mode === 'lost-open') return route.abort()
      return route.fulfill({ status: 201, json: dispute })
    }
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  return { writes, reads }
}
test('open rejected-return dispute with confirmation, then send a message', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto(`/returns/${id}`)
  await page.getByRole('link', { name: 'View or open a dispute' }).click()
  await page.getByLabel('Explain your dispute').fill('Please reconsider this return.')
  await page.getByRole('button', { name: 'Review message' }).click()
  expect(calls.writes).toHaveLength(0)
  await page.getByRole('button', { name: 'Confirm opening dispute' }).dblclick()
  await expect(page.getByRole('heading', { name: 'Open', exact: true })).toBeVisible()
  expect(calls.writes).toHaveLength(1)
  expect(calls.writes[0]).toEqual({ path: `/api/v1/returns/${id}/dispute`, body: { message: 'Please reconsider this return.' }, authorization: 'Bearer dispute-test-token' })
  await page.getByLabel('Your message').fill('Here is more detail about the fit.')
  await page.getByRole('button', { name: 'Review message' }).click()
  await page.getByRole('button', { name: 'Confirm send message' }).click()
  await expect(page.getByRole('article', { name: 'Dispute conversation' }).getByText('Here is more detail about the fit.')).toBeVisible()
  expect(calls.writes[1].body).toEqual({ body: 'Here is more detail about the fit.' })
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))).not.toContain('Here is more detail')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('dispute-conversation.png'), fullPage: true })
})
for (const mode of ['lost-open', 'lost-message'] as const) test(`${mode} never replays a write and stays locked after refresh`, async ({ page }) => {
  const calls = await setup(page, mode)
  await page.goto(`/returns/${id}/dispute`)
  await page.getByLabel(mode === 'lost-open' ? 'Explain your dispute' : 'Your message').fill('Please check this information.')
  await page.getByRole('button', { name: 'Review message' }).click()
  await page.getByRole('button', { name: mode === 'lost-open' ? 'Confirm opening dispute' : 'Confirm send message' }).click()
  await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.getByRole('button', { name: 'Refresh dispute' }).click()
  await expect(page.getByRole('heading', { name: 'Open', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Review message' })).toBeDisabled()
  expect(calls.writes).toHaveLength(1)
})
test('resolved disputes show resolution without a message form', async ({ page }) => {
  await setup(page, 'resolved'); await page.goto(`/returns/${id}/dispute`)
  await expect(page.getByText('The return was reconsidered.')).toBeVisible()
  await expect(page.getByLabel('Your message')).not.toBeVisible()
})
for (const mode of ['denied', 'malformed'] as const) test(`${mode} dispute responses never enable opening or replies`, async ({ page }) => {
  const calls = await setup(page, mode); await page.goto(`/returns/${id}/dispute`)
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Review message' })).not.toBeVisible()
  expect(calls.writes).toHaveLength(0)
})
test('non-rejected returns cannot open disputes', async ({ page }) => {
  await setup(page, 'not-rejected'); await page.goto(`/returns/${id}/dispute`)
  await expect(page.getByText('A new dispute is available only after a return is rejected.')).toBeVisible()
  await expect(page.getByLabel('Explain your dispute')).not.toBeVisible()
})
test('guests cannot access account disputes', async ({ page }) => {
  const calls = await setup(page, 'guest'); await page.goto(`/returns/${id}/dispute`)
  await expect(page.getByRole('link', { name: 'Sign in', exact: true })).toBeVisible()
  expect(calls.reads).toHaveLength(0); expect(calls.writes).toHaveLength(0)
})
test('short reasons and business-rule errors do not claim success', async ({ page }) => {
  const calls = await setup(page, 'rejected-write'); await page.goto(`/returns/${id}/dispute`)
  await page.getByLabel('Explain your dispute').fill('short')
  await page.getByRole('button', { name: 'Review message' }).click()
  await expect(page.getByRole('alert')).toContainText('10–2,000')
  expect(calls.writes).toHaveLength(0)
  await page.getByLabel('Explain your dispute').fill('Please reconsider this return.')
  await page.getByRole('button', { name: 'Review message' }).click()
  await page.getByRole('button', { name: 'Confirm opening dispute' }).click()
  await expect(page.getByRole('alert')).toContainText('already open')
  await expect(page.getByText('Dispute opened.', { exact: false })).not.toBeVisible()
})
