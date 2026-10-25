import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111'
const row = { id, type: 'order', title: 'Order dispatched', body: '<b>Your order is on its way.</b>', is_read: false, action_url: `/orders/${id}`, created_at: '2026-10-23T01:00:00Z' }
async function setup(page: Page, mode: 'normal' | 'many' | 'lost' | 'missing' | 'denied' | 'invalid' | 'guest' | 'empty' = 'normal') {
  const calls = { reads: [] as string[], writes: [] as string[] }
  let rows = mode === 'empty' ? [] : mode === 'many' ? Array.from({ length: 21 }, (_, i) => ({ ...row, id: `11111111-1111-4111-8111-${String(i).padStart(12, '0')}`, title: `Update ${i + 1}` })) : [row, { ...row, id: '22222222-2222-4222-8222-222222222222', title: 'Older update', is_read: true, action_url: 'javascript:alert(1)' }]
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(mode === 'guest' ? { status: 401, json: { error: { message: 'Guest' } } } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'buyer', first_name: 'Sara', email: 'sara@example.test', role: 'customer' } })
    if (path.endsWith('/auth/logout')) return route.fulfill({ status: 204 })
    if (path.includes('/notifications')) {
      expect(req.headers().authorization).toBe('Bearer fixture-token')
      if (req.method() === 'POST') {
        calls.writes.push(path)
        if (mode === 'denied') return route.fulfill({ status: 403, json: { error: { message: 'Read update denied.' } } })
        if (mode === 'missing') { rows = rows.filter((item) => item.id !== id); return route.fulfill({ json: { marked: false } }) }
        const all = path.endsWith('/read-all')
        const count = rows.filter((item) => !item.is_read).length
        rows = rows.map((item) => all || path.includes(item.id) ? { ...item, is_read: true } : item)
        if (mode === 'lost') return route.abort('failed')
        return route.fulfill({ json: all ? { updated_count: count + 2 } : { marked: true } })
      }
      calls.reads.push(url.search)
      const filtered = url.searchParams.get('unread_only') === 'true' ? rows.filter((item) => !item.is_read) : rows
      const index = Number(url.searchParams.get('page'))
      return route.fulfill({ json: { data: filtered.slice((index - 1) * 20, index * 20), total: filtered.length, page: mode === 'invalid' ? 99 : index, unread_count: rows.filter((item) => !item.is_read).length } })
    }
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  return calls
}
test('inbox reads render safe text and links without marking anything read', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto('/account')
  await page.getByRole('link', { name: 'View your notifications' }).click()
  await expect(page.getByText('1 unread notifications (when loaded)')).toBeVisible()
  await expect(page.getByText('<b>Your order is on its way.</b>', { exact: true })).toHaveCount(2)
  await expect(page.locator('.account-card b')).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'View related page' })).toHaveAttribute('href', `/orders/${id}`)
  await expect(page.getByText('The linked destination is not supported here.')).toBeVisible()
  expect(calls.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('notification-inbox.png'), fullPage: true })
})
test('individual read marking refreshes server counts and unread filtering', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/account/inbox')
  await page.getByRole('checkbox', { name: 'Show unread only' }).check()
  await expect(page.getByRole('heading', { name: 'Older update' })).not.toBeVisible()
  await page.getByRole('button', { name: 'Mark Order dispatched as read' }).click()
  await expect(page.getByText('Notification marked as read.', { exact: true })).toBeVisible()
  await expect(page.getByText('No unread notifications.', { exact: true })).toBeVisible()
  await expect(page.getByText('0 unread notifications (when loaded)')).toBeVisible()
  expect(calls.writes).toEqual([`/api/v1/notifications/${id}/read`])
})
test('pagination and confirmed bulk marking cover the whole account', async ({ page }) => {
  const calls = await setup(page, 'many')
  await page.goto('/account/inbox')
  await page.getByRole('button', { name: 'Next notifications' }).click()
  await expect(page.getByRole('heading', { name: 'Update 21', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Next notifications' })).toBeDisabled()
  await page.getByRole('button', { name: 'Mark all as read', exact: true }).click()
  await expect(page.getByText('including other pages and archived notifications', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Keep unread notifications' }).click()
  expect(calls.writes).toEqual([])
  await page.getByRole('button', { name: 'Mark all as read', exact: true }).click()
  await page.getByRole('button', { name: 'Yes, mark all as read', exact: true }).click()
  await expect(page.getByText('Server marked 23 notifications as read', { exact: false })).toBeVisible()
  await expect(page.getByText('0 unread notifications (when loaded)')).toBeVisible()
  expect(calls.writes).toEqual(['/api/v1/notifications/read-all'])
})
test('lost writes lock future changes even after refresh', async ({ page }) => {
  const calls = await setup(page, 'lost')
  await page.goto('/account/inbox')
  await page.getByRole('button', { name: 'Mark Order dispatched as read' }).click()
  await expect(page.getByText('Further changes are locked', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Refresh inbox' }).click()
  await expect(page.getByText('0 unread notifications (when loaded)')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Mark all as read', exact: true })).toBeDisabled()
  expect(calls.writes).toHaveLength(1)
})
test('not-found response is not reported as a successful read', async ({ page }) => {
  await setup(page, 'missing')
  await page.goto('/account/inbox')
  await page.getByRole('button', { name: 'Mark Order dispatched as read' }).click()
  await expect(page.getByText('This notification was not found for your account.', { exact: false })).toBeVisible()
  await expect(page.getByText('Notification marked as read.', { exact: true })).not.toBeVisible()
})
test('definite rejection leaves read status unchanged', async ({ page }) => {
  const calls = await setup(page, 'denied')
  await page.goto('/account/inbox')
  await page.getByRole('button', { name: 'Mark Order dispatched as read' }).click()
  await expect(page.getByRole('alert')).toContainText('Read update denied.')
  await expect(page.getByText('1 unread notifications (when loaded)')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Mark Order dispatched as read' })).toBeEnabled()
  expect(calls.writes).toHaveLength(1)
})
test('invalid responses hide notification content and write controls', async ({ page }) => {
  await setup(page, 'invalid')
  await page.goto('/account/inbox')
  await expect(page.getByRole('alert')).toContainText('could not be verified')
  await expect(page.getByRole('heading', { name: 'Order dispatched' })).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'Mark all as read', exact: true })).not.toBeVisible()
})
test('empty inbox is distinct from failures', async ({ page }) => {
  await setup(page, 'empty')
  await page.goto('/account/inbox')
  await expect(page.getByText('Your inbox is empty.', { exact: true })).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})
test('guests never request the inbox', async ({ page }) => {
  const calls = await setup(page, 'guest')
  await page.goto('/account/inbox')
  await expect(page.getByText('Sign in to manage your account.')).toBeVisible()
  expect(calls.reads).toEqual([])
})
test('sign-out removes inbox content before back navigation', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/account/inbox')
  await expect(page.getByRole('heading', { name: 'Order dispatched' })).toBeVisible()
  await page.getByRole('link', { name: 'Back to account' }).click()
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Sign out', exact: true })).not.toBeVisible()
  const reads = calls.reads.length
  await page.goBack()
  await expect(page.getByText('Sign in to manage your account.')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Order dispatched' })).not.toBeVisible()
  expect(calls.reads).toHaveLength(reads)
  expect(calls.writes).toEqual([])
})
