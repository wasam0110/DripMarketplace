import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const id = '11111111-1111-4111-8111-111111111111'
const photoId = '22222222-2222-4222-8222-222222222222'
const url = 'https://images.example.test/review.webp'
async function picture(page: Page) {
  const encoded = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width = 24; canvas.height = 24
    const context = canvas.getContext('2d')!; context.fillStyle = '#203c32'; context.fillRect(0, 0, 24, 24)
    return canvas.toDataURL('image/png').split(',')[1]
  })
  return { name: 'fixture.png', mimeType: 'image/png', buffer: Buffer.from(encoded, 'base64') }
}
async function setup(page: Page, mode: 'normal' | 'existing' | 'lost' | 'foreign' | 'locked' | 'limit' = 'normal') {
  let images = mode === 'existing' ? [{ id: photoId, url, sort_order: 0 }] : mode === 'limit' ? Array.from({ length: 5 }, (_, index) => ({ id: `22222222-2222-4222-8222-22222222222${index}`, url, sort_order: index })) : []
  let status = mode === 'locked' ? 'rejected' : 'approved'
  const writes: string[] = []
  await page.route('https://images.example.test/**', (route) => route.fulfill({ status: 404 }))
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', email: 'buyer@example.test', role: 'customer' } })
    if (path.includes(`/me/reviews/${id}/images`)) {
      if (req.method() !== 'GET') {
        writes.push(req.method())
        expect(req.headers().authorization).toBe('Bearer fixture-token')
        if (req.method() === 'POST') {
          expect(req.headers()['content-type']).toContain('multipart/form-data; boundary=')
          expect(req.postDataBuffer()!.toString('latin1')).toContain('name="image"; filename="fixture.png"')
          images = [{ id: photoId, url, sort_order: 0 }]
        } else { expect(path).toContain(photoId); images = [] }
        status = 'pending'
        if (mode === 'lost') return route.abort()
      }
      return route.fulfill({ json: { id, product_id: id, user: { id: mode === 'foreign' ? 'other' : 'owner' }, status, images } })
    }
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  await page.goto(`/account/reviews/${id}/photos`)
  return writes
}
test('local preview uploads only on confirmation and returns to moderation', async ({ page }, info) => {
  const writes = await setup(page)
  await page.getByLabel('Choose review photo').setInputFiles(await picture(page))
  await expect(page.getByRole('img', { name: 'Selected review photo preview' })).toBeVisible()
  expect(writes).toHaveLength(0)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.screenshot({ path: info.outputPath('review-photo-preview.png'), fullPage: true })
  await page.getByRole('button', { name: 'Upload selected review photo' }).dblclick()
  await expect(page.getByText('Photo uploaded. The review now awaits moderation.')).toBeVisible()
  await expect(page.getByText(/1 of 5 photos/)).toBeVisible()
  expect(writes).toEqual(['POST'])
})
test('removal requires confirmation and reports queued storage cleanup', async ({ page }) => {
  const writes = await setup(page, 'existing')
  await page.getByRole('button', { name: 'Remove photo 1', exact: true }).click()
  expect(writes).toHaveLength(0)
  await page.getByRole('button', { name: 'Keep photo' }).click()
  await page.getByRole('button', { name: 'Remove photo 1', exact: true }).click()
  await page.getByRole('button', { name: 'Yes, remove photo' }).click()
  await expect(page.getByText('No photos attached.')).toBeVisible()
  await expect(page.getByText(/Storage cleanup is queued/)).toBeVisible()
  expect(writes).toEqual(['DELETE'])
})
test('uncertain uploads stay locked after read refresh', async ({ page }) => {
  const writes = await setup(page, 'lost')
  await page.getByLabel('Choose review photo').setInputFiles(await picture(page))
  await page.getByRole('button', { name: 'Upload selected review photo' }).click()
  await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.getByRole('button', { name: 'Refresh review photos' }).click()
  await expect(page.getByText(/1 of 5 photos/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Remove photo 1', exact: true })).toBeDisabled()
  expect(writes).toEqual(['POST'])
})
test('foreign metadata hides photo controls', async ({ page }) => {
  await setup(page, 'foreign')
  await expect(page.getByRole('alert')).toContainText('could not be verified')
  await expect(page.getByLabel('Choose review photo')).not.toBeVisible()
})
test('rejected reviews cannot change photos', async ({ page }) => {
  await setup(page, 'locked')
  await expect(page.getByLabel('Choose review photo')).toBeDisabled()
})
test('five photos prevent further uploads', async ({ page }) => {
  await setup(page, 'limit')
  await expect(page.getByText('The five-photo limit has been reached.')).toBeVisible()
  await expect(page.getByLabel('Choose review photo')).not.toBeVisible()
})
test('invalid file formats never upload', async ({ page }) => {
  const writes = await setup(page)
  await page.getByLabel('Choose review photo').setInputFiles({ name: 'bad.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg/>') })
  await expect(page.getByRole('alert')).toContainText('JPEG, PNG or WebP')
  await expect(page.getByRole('button', { name: 'Upload selected review photo' })).toBeDisabled()
  expect(writes).toHaveLength(0)
})
