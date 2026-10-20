import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

async function stubPublicApi(page: Page) {
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.includes('/auth/')) return route.fulfill({
      status: 401, json: { error: { code: 'UNAUTHORIZED', message: 'Sign in to continue.' } },
    })
    return route.fulfill({ json: { data: [], pagination: { next_cursor: null, has_next: false, limit: 20, page: 1, per_page: 24, total: 0 } } })
  })
}

test('homepage renders without JS errors, overflow or broken local assets', async ({ page }, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await stubPublicApi(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Good labels.Great finds.')
  await expect(page.getByText('Room for something good.')).toBeVisible()
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= window.innerWidth)).toBe(true)
  const loaded = await page.locator('.hero-image img, .logo img').evaluateAll((images) =>
    images.every((image) => (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0))
  expect(loaded).toBe(true)
  expect(errors).toEqual([])
  await page.screenshot({ path: testInfo.outputPath('homepage.png'), fullPage: true })
})

test('navigation search is keyboard accessible and changes the catalogue query', async ({ page }) => {
  await stubPublicApi(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Search clothing' }).click()
  const field = page.getByRole('searchbox', { name: 'Search clothing' })
  await expect(field).toBeFocused()
  await field.fill('linen')
  await field.press('Enter')
  await expect(page).toHaveURL(/\/clothing\?q=linen/)
  await expect(page.getByRole('heading', { name: 'Your edit: “linen”' })).toBeVisible()
  await expect(page.locator('#main')).toBeFocused()
})

test('mobile menu or desktop links provide real navigation', async ({ page }, testInfo) => {
  await stubPublicApi(page)
  await page.goto('/')
  if (testInfo.project.name === 'mobile') {
    await page.getByRole('button', { name: 'Open menu' }).click()
    await page.getByRole('navigation', { name: 'Mobile navigation' }).getByRole('link', { name: 'Brands' }).click()
    await expect(page.getByRole('navigation', { name: 'Mobile navigation' })).not.toBeVisible()
  } else {
    await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Brands', exact: true }).click()
  }
  await expect(page.getByRole('heading', { name: 'The brand directory' })).toBeVisible()
})

for (const path of ['/', '/login', '/register', '/clothing']) {
  test(`accessibility scan and responsive layout: ${path}`, async ({ page }, testInfo) => {
    await stubPublicApi(page)
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    if (path === '/login' || path === '/register') {
      await expect(page.getByRole('button', { name: path === '/login' ? 'Sign in' : 'Create account', exact: true })).toBeEnabled()
    } else {
      await expect(page.getByText('Room for something good.')).toBeVisible()
    }
    expect(await page.locator('body').evaluate((body) => body.scrollWidth <= window.innerWidth)).toBe(true)
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    expect(results.violations).toEqual([])
    if (path === '/login') await page.screenshot({ path: testInfo.outputPath('login.png'), fullPage: true })
  })
}

test('reduced motion removes hover transitions', async ({ page }) => {
  await stubPublicApi(page)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  expect(await page.locator('.hero .button').evaluate((element) => getComputedStyle(element).transitionDuration)).toBe('0s')
})

test('small phones keep the header and account control accessible', async ({ page }) => {
  await stubPublicApi(page)
  await page.setViewportSize({ width: 320, height: 740 })
  await page.goto('/login')
  await expect(page.locator('.account-link')).toHaveAccessibleName('Account')
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= window.innerWidth)).toBe(true)
})

test('live development proxy reaches the existing backend without writes', async ({ request }) => {
  const health = await request.get('/api/v1/health')
  expect(health.ok()).toBe(true)
  expect(await health.json()).toMatchObject({ status: 'ok', database: 'ok', redis: 'ok' })
  const catalogue = await request.get('/api/v1/products?limit=4')
  expect(catalogue.ok()).toBe(true)
  const result = await catalogue.json()
  expect(Array.isArray(result.data)).toBe(true)
  expect(result.pagination).toHaveProperty('has_next')
})
