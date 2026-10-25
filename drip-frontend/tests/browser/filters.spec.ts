import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const category = '11111111-1111-4111-8111-111111111111'
async function setup(page: Page, failCategories = false) {
  const reads: string[] = []
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.includes('/auth/')) return route.fulfill({ status: 401, json: { error: { message: 'Guest' } } })
    if (url.pathname.endsWith('/categories')) {
      if (failCategories) return route.fulfill({ status: 503, json: { error: { message: 'Categories unavailable' } } })
      return route.fulfill({ json: { data: [{ id: category, name: 'Shirts', parent_id: null }] } })
    }
    if (url.pathname.endsWith('/products')) reads.push(url.search)
    return route.fulfill({ json: { data: [], pagination: { has_next: false, next_cursor: null, limit: 20 } } })
  })
  return reads
}

test('filters survive search, sorting and reload; clear keeps search', async ({ page }, info) => {
  const reads = await setup(page)
  await page.goto('/clothing?cursor=old')
  await page.getByText('Refine your edit', { exact: true }).click()
  await page.getByLabel('Category', { exact: true }).selectOption(category)
  await page.getByLabel('Minimum price (PKR)', { exact: true }).fill('1000')
  await page.getByLabel('Maximum price (PKR)', { exact: true }).fill('5000')
  await page.getByLabel('Letter sizes', { exact: true }).fill('S, M')
  await page.getByLabel('Colours', { exact: true }).fill('Ivory')
  await page.getByLabel('On sale', { exact: true }).check()
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click()
  await expect.poll(() => reads.at(-1)).toContain('category_id=')
  expect(new URL(page.url()).searchParams.has('cursor')).toBe(false)
  expect(new URLSearchParams(reads.at(-1)).getAll('size_alpha')).toEqual(['S', 'M'])
  await page.getByRole('searchbox', { name: 'Search clothing', exact: true }).fill('linen')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await page.getByRole('combobox', { name: 'Sort', exact: true }).selectOption('price_asc')
  await page.reload()
  await expect(page.getByLabel('Category', { exact: true })).toHaveValue(category)
  await expect(page.getByLabel('Minimum price (PKR)', { exact: true })).toHaveValue('1000')
  await expect(page.getByLabel('On sale', { exact: true })).toBeChecked()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('filters.png'), fullPage: true })
  await page.getByRole('button', { name: 'Clear filters', exact: true }).click()
  expect(new URL(page.url()).searchParams.get('q')).toBe('linen')
  expect(new URL(page.url()).searchParams.get('sort')).toBe('price_asc')
  expect(new URL(page.url()).searchParams.has('category_id')).toBe(false)
})

test('invalid URL filters block product reads and can be cleared', async ({ page }) => {
  const reads = await setup(page)
  await page.goto('/clothing?min_price=4000&max_price=1000')
  await expect(page.getByRole('alert')).toContainText('Minimum price must not exceed')
  expect(reads).toHaveLength(0)
  await page.getByRole('button', { name: 'Clear filters', exact: true }).click()
  await expect.poll(() => reads.length).toBeGreaterThan(0)
})

test('category failures retry without blocking other filters', async ({ page }) => {
  await setup(page, true)
  await page.goto('/clothing')
  await page.getByText('Refine your edit', { exact: true }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await page.route('**/api/v1/categories', (route) => route.fulfill({ json: { data: [{ id: category, name: 'Shirts', parent_id: null }] } }))
  await page.getByRole('button', { name: 'Retry categories' }).click()
  await expect(page.getByRole('option', { name: 'Shirts', exact: true })).toHaveCount(1)
  await page.getByLabel('Minimum price (PKR)', { exact: true }).fill('5000')
  await page.getByLabel('Maximum price (PKR)', { exact: true }).fill('1000')
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Minimum price must not exceed')
  expect(new URL(page.url()).searchParams.has('min_price')).toBe(false)
})
