import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const id = '11111111-1111-4111-8111-111111111111'
const review = { id: '22222222-2222-4222-8222-222222222222', product_id: id, rating: 4, title: 'Beautiful fabric', body: '<b>Comfortable</b> and easy to wear.', status: 'approved', is_verified_purchase: true, created_at: '2026-10-20T12:00:00Z', user: { id: 'author', first_name: 'Ayesha', last_name: null }, images: [], helpful_count: 3, unhelpful_count: 1 }
async function setup(page: Page, mode: 'guest' | 'success' | 'denied' | 'lost' = 'guest') {
  const writes: unknown[] = []
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/auth/refresh')) return mode === 'guest'
      ? route.fulfill({ status: 401, json: { error: { message: 'Guest' } } })
      : route.fulfill({ json: { access_token: 'fixture-token' } })
    if (url.pathname.endsWith('/auth/me')) return route.fulfill({ json: { id: 'buyer', email: 'buyer@example.test', first_name: 'Buyer', last_name: null, role: 'customer', has_verified_email: true } })
    if (url.pathname.endsWith('/reviews')) {
      if (route.request().method() === 'POST') {
        writes.push(route.request().postDataJSON())
        if (mode === 'lost') return route.abort('failed')
        if (mode === 'denied') return route.fulfill({ status: 409, json: { error: { message: 'You have already reviewed this product.' } } })
        return route.fulfill({ status: 201, json: { ...review, status: 'pending' } })
      }
      const second = url.searchParams.get('page') === '2'
      return route.fulfill({ json: { data: [{ ...review, title: second ? 'Second page review' : review.title }], total: 11, page: second ? 2 : 1, per_page: 10, pages: 2, avg_rating: 4, rating_breakdown: { '4': 11 } } })
    }
    if (url.pathname.endsWith(`/products/${id}`)) return route.fulfill({ json: {
      id, name: 'Linen shirt', slug: 'linen-shirt', brand_name: 'Studio Label', price: '4500', sale_price: null, primary_image: null,
      has_stock: false, description: 'Everyday linen.', images: [], variants: [], avg_rating: 4, review_count: 11,
      seller: { id: 'seller', slug: 'studio', brand_name: 'Studio Label', return_policy: null },
    } })
    return route.fulfill({ json: { items: [], item_count: 0, subtotal: '0', shipping_fee: '0', total: '0' } })
  })
  return writes
}

async function fillReview(page: Page) {
  await page.getByRole('combobox', { name: 'Rating', exact: true }).selectOption('5')
  await page.getByLabel('Review title (optional)', { exact: true }).fill('My perspective')
  await page.getByLabel('Your review (optional)', { exact: true }).fill('Soft linen.')
}

test('public reviews show ratings, plain text and pagination without guest submission', async ({ page }, info) => {
  await setup(page)
  await page.goto(`/products/${id}`)
  await expect(page.getByRole('heading', { name: 'Beautiful fabric' })).toBeVisible()
  await expect(page.getByText('<b>Comfortable</b> and easy to wear.', { exact: true })).toBeVisible()
  await expect(page.getByText('4 out of 5 · Verified purchase', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Sign in to write a review' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Submit review' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Helpful', exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Next reviews' }).click()
  await expect(page.getByRole('heading', { name: 'Second page review' })).toBeVisible()
  await page.getByRole('button', { name: 'Previous reviews' }).click()
  await expect(page.getByRole('heading', { name: 'Beautiful fabric' })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.locator('.product-reviews').screenshot({ path: info.outputPath('reviews.png') })
})

test('signed-in submission confirms moderation without publishing or persisting draft', async ({ page }) => {
  const writes = await setup(page, 'success')
  await page.goto(`/products/${id}`)
  await fillReview(page)
  await page.getByRole('button', { name: 'Submit review', exact: true }).click()
  await expect(page.getByText('Review received and awaiting moderation.', { exact: false })).toBeVisible()
  expect(writes).toEqual([{ product_id: id, rating: 5, title: 'My perspective', body: 'Soft linen.' }])
  await expect(page.getByRole('heading', { name: 'My perspective' })).toHaveCount(0)
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain('Soft linen.')
})

test('server rejection preserves text and does not claim success', async ({ page }) => {
  const writes = await setup(page, 'denied')
  await page.goto(`/products/${id}`)
  await fillReview(page)
  await page.getByRole('button', { name: 'Submit review', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('already reviewed')
  await expect(page.getByLabel('Your review (optional)', { exact: true })).toHaveValue('Soft linen.')
  expect(writes).toHaveLength(1)
})

test('lost submission is not replayed and further submission is blocked', async ({ page }) => {
  const writes = await setup(page, 'lost')
  await page.goto(`/products/${id}`)
  await fillReview(page)
  await page.getByRole('button', { name: 'Submit review', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Do not submit it again')
  await expect(page.getByRole('button', { name: 'Submit review', exact: true })).toBeDisabled()
  expect(writes).toHaveLength(1)
})

test('failed public reviews retry to an honest empty state', async ({ page }) => {
  await setup(page)
  await page.route('**/reviews?*', (route) => route.fulfill({ status: 503, json: { error: { message: 'Reviews unavailable' } } }))
  await page.goto(`/products/${id}`)
  const section = page.getByRole('region', { name: 'Reviews of this piece' })
  await expect(section.getByRole('alert')).toContainText('Reviews unavailable')
  await page.route('**/reviews?*', (route) => route.fulfill({ json: { data: [], total: 0, page: 1, per_page: 10, pages: 0, avg_rating: null, rating_breakdown: {} } }))
  await section.getByRole('button', { name: 'Retry reviews' }).click()
  await expect(section.getByText('No approved reviews yet.', { exact: true })).toBeVisible()
  await expect(section.getByRole('button', { name: 'Next reviews' })).toHaveCount(0)
})

for (const helpful of [true, false]) {
  test(`signed-in ${helpful ? 'helpful' : 'unhelpful'} vote does not invent counts or replacement`, async ({ page }, info) => {
    await setup(page, 'success')
    const votes: unknown[] = []
    await page.route('**/reviews/*/helpful', async (route) => {
      expect(route.request().headers().authorization).toBe('Bearer fixture-token')
      votes.push(route.request().postDataJSON())
      return route.fulfill({ status: 204 })
    })
    await page.goto(`/products/${id}`)
    const button = page.getByRole('button', { name: helpful ? 'Helpful' : 'Not helpful', exact: true })
    await expect(button).toBeEnabled()
    if (helpful) {
      expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.screenshot({ path: info.outputPath('review-voting.png'), fullPage: true })
    }
    await button.click()
    await expect(page.getByText('Vote request accepted.', { exact: false })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Helpful', exact: true })).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Not helpful', exact: true })).toBeDisabled()
    await expect(page.getByText('3 helpful · 1 not helpful (when loaded)', { exact: true })).toBeVisible()
    expect(votes).toEqual([{ helpful }])
  })
}

test('authors cannot vote on their own reviews', async ({ page }) => {
  await setup(page, 'success')
  await page.route('**/products/*/reviews?*', (route) => route.fulfill({ json: { data: [{ ...review, user: { ...review.user, id: 'buyer' } }], total: 1, page: 1, per_page: 10, pages: 1, avg_rating: 4, rating_breakdown: { '4': 1 } } }))
  await page.goto(`/products/${id}`)
  await expect(page.getByText('You cannot vote on your own review.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Helpful', exact: true })).toHaveCount(0)
})

test('an uncertain vote is not replayed', async ({ page }) => {
  await setup(page, 'success')
  let votes = 0
  await page.route('**/reviews/*/helpful', (route) => { votes++; return route.abort('failed') })
  await page.goto(`/products/${id}`)
  await page.getByRole('button', { name: 'Helpful', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('vote could not be confirmed')
  await expect(page.getByRole('button', { name: 'Not helpful', exact: true })).toBeDisabled()
  expect(votes).toBe(1)
})

test('vote rejection shows the server error without success', async ({ page }) => {
  await setup(page, 'success')
  await page.route('**/reviews/*/helpful', (route) => route.fulfill({ status: 403, json: { error: { message: 'This review is no longer public.' } } }))
  await page.goto(`/products/${id}`)
  await page.getByRole('button', { name: 'Helpful', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('no longer public')
  await expect(page.getByText('Vote request accepted.', { exact: false })).toHaveCount(0)
})
