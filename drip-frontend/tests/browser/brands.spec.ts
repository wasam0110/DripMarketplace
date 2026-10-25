import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const cursor = 'next+/=page'
async function fixture(page: Page, mode: 'normal' | 'empty' | 'retry' = 'normal') {
  let failed = false
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.includes('/auth/')) return route.fulfill({ status: 401, json: { error: { message: 'Guest' } } })
    if (url.pathname.endsWith('/brands/studio')) return route.fulfill({ json: {
      id: '11111111-1111-4111-8111-111111111111', slug: 'studio', brand_name: 'Studio Label',
      description: 'Considered everyday pieces.', return_policy: 'Contact the brand about returns.', logo_url: null,
    } })
    if (url.pathname.endsWith('/brands/studio/products')) {
      const later = url.searchParams.get('cursor') === cursor
      if (later && mode === 'retry' && !failed) {
        failed = true
        return route.fulfill({ status: 503, json: { error: { message: 'Collection temporarily unavailable' } } })
      }
      return route.fulfill({ json: {
        data: later && mode === 'empty' ? [] : [{
          id: later ? '22222222-2222-4222-8222-222222222222' : '33333333-3333-4333-8333-333333333333',
          slug: later ? 'trousers' : 'shirt', name: later ? 'Linen trousers' : 'Linen shirt',
          brand_name: 'Studio Label', price: '4500', sale_price: null, primary_image: null, has_stock: true,
        }], pagination: { has_next: !later, next_cursor: later ? null : cursor, limit: 20 },
      } })
    }
    return route.fulfill({ json: { data: [], pagination: { total: 0, per_page: 24, page: 1 } } })
  })
}

test('brand collection pages preserve the label, cursor and browser history', async ({ page }, info) => {
  await fixture(page)
  await page.goto('/brands/studio')
  await expect(page.getByRole('heading', { name: 'Linen shirt' })).toBeVisible()
  await page.getByRole('button', { name: 'Next pieces' }).click()
  await expect(page.getByRole('heading', { name: 'Linen trousers' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('cursor')).toBe(cursor)
  await expect(page.getByRole('button', { name: 'Next pieces' })).toHaveCount(0)
  await expect(page.getByRole('heading', { level: 1, name: 'Studio Label' })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('brand-collection.png'), fullPage: true })
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Linen trousers' })).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Linen shirt' })).toBeVisible()
  await page.goForward()
  await expect(page.getByRole('heading', { name: 'Linen trousers' })).toBeVisible()
  await page.getByRole('button', { name: 'Back to first page' }).click()
  await expect(page.getByRole('heading', { name: 'Linen shirt' })).toBeVisible()
  await expect(page).toHaveURL(/\/brands\/studio$/)
})

test('an empty later page can return to the same brand collection', async ({ page }) => {
  await fixture(page, 'empty')
  await page.goto(`/brands/studio?${new URLSearchParams({ cursor })}`)
  await expect(page.getByRole('heading', { name: 'Room for something good.' })).toBeVisible()
  await page.getByRole('button', { name: 'Back to first page' }).click()
  await expect(page.getByRole('heading', { name: 'Linen shirt' })).toBeVisible()
  await expect(page).toHaveURL(/\/brands\/studio$/)
})

test('failed collection page retries the same cursor without showing stale pieces', async ({ page }) => {
  await fixture(page, 'retry')
  await page.goto('/brands/studio')
  await page.getByRole('button', { name: 'Next pieces' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Linen shirt' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByRole('heading', { name: 'Linen trousers' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('cursor')).toBe(cursor)
})
