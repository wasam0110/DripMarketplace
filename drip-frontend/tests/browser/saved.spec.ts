import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const id = '11111111-1111-4111-8111-111111111111'
const other = '22222222-2222-4222-8222-222222222222'
const key = 'wearhowz.saved-pieces.v1'
const product = { id, slug: 'linen-shirt', name: 'Linen shirt', brand_name: 'Studio Label', price: '4500', sale_price: null, primary_image: null, has_stock: true,
  description: 'An easy everyday layer.', avg_rating: 0, review_count: 0, images: [], variants: [], seller: { id: other, slug: 'studio', brand_name: 'Studio Label', return_policy: null } }
async function setup(page: Page) {
  const requests: { path: string; method: string }[] = []
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    requests.push({ path, method: route.request().method() })
    if (path.includes('/auth/')) return route.fulfill({ status: 401, json: { error: { message: 'Guest' } } })
    if (path.endsWith('/products')) return route.fulfill({ json: { data: [product], pagination: { has_next: false, next_cursor: null, limit: 20 } } })
    if (path.endsWith(`/products/${id}`)) return route.fulfill({ json: product })
    if (path.endsWith(`/products/${other}`)) return route.fulfill({ status: 404, json: { error: { message: 'Unavailable' } } })
    return route.fulfill({ json: { data: [], pagination: { page: 1, per_page: 20, total: 0 } } })
  })
  return requests
}
test('save from catalogue, reload, view live product and remove without backend writes', async ({ page }, info) => {
  const requests = await setup(page)
  await page.goto('/clothing')
  await page.getByRole('button', { name: 'Save Linen shirt on this device' }).click()
  await expect(page.getByRole('button', { name: 'Remove Linen shirt from saved pieces' })).toHaveAttribute('aria-pressed', 'true')
  expect(await page.evaluate((key) => localStorage.getItem(key), key)).toBe(JSON.stringify([id]))
  await page.goto('/saved')
  await expect(page.getByRole('heading', { name: 'Linen shirt', exact: true })).toBeVisible()
  await expect(page.getByText('Saved only in this browser', { exact: false })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('button', { name: 'Remove Linen shirt from saved pieces' })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('saved-pieces.png'), fullPage: true })
  await page.getByRole('heading', { name: 'Linen shirt', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Linen shirt' })).toBeVisible()
  await page.getByRole('button', { name: 'Remove Linen shirt from saved pieces' }).click()
  await page.goto('/saved')
  await expect(page.getByRole('heading', { name: 'Make room for your next favourite.' })).toBeVisible()
  expect(requests.filter(({ path, method }) => !path.includes('/auth/') && method !== 'GET')).toEqual([])
})
test('unavailable saved references remain removable and never show stale prices', async ({ page }) => {
  await setup(page)
  await page.addInitScript(({ key, other }) => localStorage.setItem(key, JSON.stringify([other])), { key, other })
  await page.goto('/saved')
  await expect(page.getByRole('heading', { name: 'This piece is no longer available.' })).toBeVisible()
  await expect(page.getByText('PKR', { exact: false })).not.toBeVisible()
  await page.getByRole('button', { name: 'Remove saved reference' }).click()
  await expect(page.getByRole('heading', { name: 'Make room for your next favourite.' })).toBeVisible()
})
test('corrupt storage is preserved until an explicit clear confirmation', async ({ page }) => {
  await setup(page)
  await page.addInitScript((key) => { localStorage.setItem(key, 'broken'); localStorage.setItem('unrelated', 'keep') }, key)
  await page.goto('/saved')
  await expect(page.getByRole('alert')).toContainText('not been overwritten')
  await page.getByRole('button', { name: 'Clear saved pieces', exact: true }).click()
  await page.getByRole('button', { name: 'Keep my saved pieces' }).click()
  expect(await page.evaluate((key) => localStorage.getItem(key), key)).toBe('broken')
  await page.getByRole('button', { name: 'Clear saved pieces', exact: true }).click()
  await page.getByRole('button', { name: 'Yes, clear this list' }).click()
  await expect(page.getByRole('heading', { name: 'Make room for your next favourite.' })).toBeVisible()
  expect(await page.evaluate(() => localStorage.getItem('unrelated'))).toBe('keep')
})
test('a blocked storage write does not claim the piece was saved', async ({ page }) => {
  await setup(page)
  await page.addInitScript((key) => {
    const original = Storage.prototype.setItem
    Storage.prototype.setItem = function (name, value) { if (name === key) throw new Error('Site storage is blocked'); original.call(this, name, value) }
  }, key)
  await page.goto(`/products/${id}`)
  await page.getByRole('button', { name: 'Save Linen shirt on this device' }).click()
  await expect(page.getByRole('alert')).toContainText('blocked')
  await expect(page.getByRole('button', { name: 'Save Linen shirt on this device' })).toHaveAttribute('aria-pressed', 'false')
  expect(await page.evaluate((key) => localStorage.getItem(key), key)).toBeNull()
})
test('another tab updates the saved list without a reload', async ({ page, context }) => {
  await setup(page)
  await page.goto('/saved')
  const otherTab = await context.newPage()
  await setup(otherTab)
  await otherTab.goto(`/products/${id}`)
  await otherTab.getByRole('button', { name: 'Save Linen shirt on this device' }).click()
  await expect(page.locator('.saved-count')).toHaveText('1 saved piece')
  await page.bringToFront()
  await expect(page.getByRole('heading', { name: 'Linen shirt', exact: true })).toBeVisible()
  await otherTab.bringToFront()
  await otherTab.getByRole('button', { name: 'Remove Linen shirt from saved pieces' }).click()
  await page.bringToFront()
  await expect(page.getByRole('heading', { name: 'Make room for your next favourite.' })).toBeVisible()
  await otherTab.close()
})
