import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const id = '11111111-1111-4111-8111-111111111111'
const product = '22222222-2222-4222-8222-222222222222'
async function setup(page: Page, mode: 'normal' | 'guest' | 'foreign' | 'lost' | 'rejected' = 'normal') {
  const writes: { method: string; body: unknown }[] = []
  let rows = [{ id, product_id: product, user: { id: mode === 'foreign' ? 'other-owner' : 'owner' }, rating: 4, title: 'My linen review', body: 'Soft fabric', status: mode === 'rejected' ? 'rejected' : 'approved' }]
  let reads = 0
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (path.endsWith('/auth/refresh')) return mode === 'guest' ? route.fulfill({ status: 401, json: {} }) : route.fulfill({ json: { access_token: 'fixture' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', email: 'owner@example.test', role: 'customer', has_verified_email: true } })
    if (path.endsWith('/me/reviews')) { reads++; return route.fulfill({ json: rows }) }
    if (path.endsWith(`/me/reviews/${id}`)) {
      const method = req.method(), body = method === 'PATCH' ? req.postDataJSON() : null
      writes.push({ method, body })
      if (mode === 'lost') return route.abort('failed')
      if (method === 'DELETE') { rows = []; return route.fulfill({ status: 204 }) }
      rows = [{ ...rows[0], ...body, status: 'pending' }]
      return route.fulfill({ json: rows[0] })
    }
    return route.fulfill({ json: { items: [], item_count: 0, subtotal: '0', shipping_fee: '0', total: '0' } })
  })
  return { writes, reads: () => reads }
}

test('edit review returns to moderation and supports clearing text', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto('/account/reviews')
  await page.getByRole('button', { name: 'Edit review' }).click()
  await page.getByRole('combobox', { name: 'Rating', exact: true }).selectOption('5')
  await page.getByLabel('Review title', { exact: true }).fill('')
  await page.getByLabel('Review text', { exact: true }).fill('Updated perspective')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('my-reviews.png'), fullPage: true })
  await page.getByRole('button', { name: 'Save review changes' }).click()
  await expect(page.getByText('Changes saved and awaiting moderation.', { exact: true })).toBeVisible()
  expect(calls.writes).toEqual([{ method: 'PATCH', body: { rating: 5, title: '', body: 'Updated perspective' } }])
  await expect(page.getByRole('heading', { name: 'Untitled review' })).toBeVisible()
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain('Updated perspective')
})

test('delete requires confirmation and only removes after success', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/account/reviews')
  await page.getByRole('button', { name: 'Delete review', exact: true }).click()
  await page.getByRole('button', { name: 'Keep review' }).click()
  expect(calls.writes).toHaveLength(0)
  await page.getByRole('button', { name: 'Delete review', exact: true }).click()
  await page.getByRole('button', { name: 'Yes, delete review' }).click()
  await expect(page.getByText('Review deleted. This cannot be undone.', { exact: true })).toBeVisible()
  expect(calls.writes).toEqual([{ method: 'DELETE', body: null }])
  await page.getByRole('button', { name: 'Refresh your reviews' }).click()
  await expect(page.getByText('You have not written any reviews yet.', { exact: true })).toBeVisible()
})

test('guests make no private review reads', async ({ page }) => {
  const calls = await setup(page, 'guest')
  await page.goto('/account/reviews')
  await expect(page.getByRole('link', { name: 'Sign in', exact: true })).toBeVisible()
  expect(calls.reads()).toBe(0)
})

test('foreign owner data is not displayed or editable', async ({ page }) => {
  await setup(page, 'foreign')
  await page.goto('/account/reviews')
  await expect(page.getByRole('alert')).toContainText('could not be verified')
  await expect(page.getByText('Soft fabric', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Edit review' })).toHaveCount(0)
})

test('rejected reviews cannot be edited', async ({ page }) => {
  await setup(page, 'rejected')
  await page.goto('/account/reviews')
  await expect(page.getByText('Rejected reviews cannot be edited.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Edit review' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Delete review', exact: true })).toBeEnabled()
})

test('uncertain deletion blocks repeat writes even after refresh', async ({ page }) => {
  const calls = await setup(page, 'lost')
  await page.goto('/account/reviews')
  await page.getByRole('button', { name: 'Delete review', exact: true }).click()
  await page.getByRole('button', { name: 'Yes, delete review' }).click()
  await expect(page.getByRole('alert')).toContainText('could not be confirmed')
  await expect(page.getByRole('button', { name: 'Yes, delete review' })).toBeDisabled()
  await page.getByRole('button', { name: 'Refresh your reviews' }).click()
  await expect(page.getByRole('button', { name: 'Delete review', exact: true })).toBeDisabled()
  expect(calls.writes).toHaveLength(1)
})
