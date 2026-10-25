import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const id = '11111111-1111-4111-8111-111111111111'
const key = 'wearhowz.saved-pieces.v1'
const item = { product_id: id, product_name: 'Linen shirt', price: '4500', sale_price: null, is_in_stock: true }
async function setup(page: Page, mode: 'normal' | 'lost' | 'denied' | 'read-error' = 'normal') {
  const writes: string[] = []
  let items: typeof item[] = []
  await page.addInitScript(({ key, id }) => localStorage.setItem(key, JSON.stringify([id])), { key, id })
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'buyer', first_name: 'Buyer', email: 'buyer@example.test', role: 'customer' } })
    if (path.includes('/me/wishlist')) {
      expect(req.headers().authorization).toBe('Bearer fixture-token')
      if (req.method() !== 'GET') {
        writes.push(req.method())
        if (mode === 'denied') return route.fulfill({ status: 403, json: { error: { message: 'Account access denied.' } } })
        if (req.method() === 'POST') { expect(req.postDataJSON()).toEqual({ product_id: id }); items = [item] }
        else { expect(path.endsWith(id)).toBe(true); items = [] }
        if (mode === 'lost') return route.abort('failed')
        if (req.method() === 'DELETE') return route.fulfill({ status: 204 })
      }
      if (mode === 'read-error') return route.fulfill({ status: 503, json: { error: { message: 'Wishlist unavailable.' } } })
      return route.fulfill({ json: { items, total: items.length } })
    }
    if (path.includes('/products/')) return route.fulfill({ status: 404, json: { error: { message: 'Unavailable' } } })
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  return writes
}

test('account copying and removal preserve device saves and survive refresh', async ({ page }, info) => {
  const writes = await setup(page)
  await page.goto('/saved')
  await expect(page.getByText('No available pieces in your account wishlist.')).toBeVisible()
  expect(writes).toEqual([])
  await page.getByRole('button', { name: 'Copy device piece 1 to account' }).click()
  await expect(page.getByText('Saved to your account. Your device copy is unchanged.')).toBeVisible()
  await page.reload()
  await expect(page.getByRole('button', { name: 'Remove Linen shirt from account' })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('account-wishlist.png'), fullPage: true })
  await page.getByRole('button', { name: 'Remove Linen shirt from account' }).click()
  await expect(page.getByText('Removed from your account wishlist. Device saves are unchanged.')).toBeVisible()
  expect(await page.evaluate((key) => localStorage.getItem(key), key)).toBe(JSON.stringify([id]))
  expect(writes).toEqual(['POST', 'DELETE'])
})

test('lost writes are not replayed and read refresh does not unlock changes', async ({ page }) => {
  const writes = await setup(page, 'lost')
  await page.goto('/saved')
  await page.getByRole('button', { name: 'Copy device piece 1 to account' }).click()
  await expect(page.getByText('The change may have reached the server.', { exact: false })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Copy device piece 1 to account' })).toBeDisabled()
  await page.getByRole('button', { name: 'Refresh account wishlist' }).click()
  await expect(page.getByRole('button', { name: 'Remove Linen shirt from account' })).toBeDisabled()
  expect(writes).toEqual(['POST'])
})

test('definite rejection does not claim success', async ({ page }) => {
  const writes = await setup(page, 'denied')
  await page.goto('/saved')
  await page.getByRole('button', { name: 'Copy device piece 1 to account' }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Account access denied.' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Copy device piece 1 to account' })).toBeEnabled()
  await expect(page.getByText('Saved to your account.', { exact: false })).not.toBeVisible()
  expect(writes).toEqual(['POST'])
})

test('failed reads block account changes without breaking device saves', async ({ page }) => {
  const writes = await setup(page, 'read-error')
  await page.goto('/saved')
  await expect(page.getByRole('alert').filter({ hasText: 'Wishlist unavailable.' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Copy device piece 1 to account' })).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'Remove saved reference' })).toBeEnabled()
  expect(writes).toEqual([])
})

test('guests never read the account wishlist', async ({ page }) => {
  await setup(page)
  let reads = 0
  await page.route('**/auth/refresh', (route) => route.fulfill({ status: 401, json: { error: { message: 'Guest' } } }))
  await page.route('**/me/wishlist', (route) => { reads++; return route.fulfill({ json: { items: [], total: 0 } }) })
  await page.goto('/saved')
  await expect(page.getByText('to manage an account wishlist.', { exact: false })).toBeVisible()
  expect(reads).toBe(0)
})

test('invalid account responses are not displayed or editable', async ({ page }) => {
  await setup(page)
  await page.route('**/me/wishlist', (route) => route.fulfill({ json: { items: [item], total: 5 } }))
  await page.goto('/saved')
  await expect(page.getByRole('alert').filter({ hasText: 'response was incomplete' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Remove Linen shirt from account' })).not.toBeVisible()
})
