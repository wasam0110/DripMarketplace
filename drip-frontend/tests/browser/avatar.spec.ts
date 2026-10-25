import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const imageUrl = 'https://images.example.test/avatar.webp'
async function picture(page: Page) {
  const encoded = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width = 32; canvas.height = 32
    const context = canvas.getContext('2d')!; context.fillStyle = '#203c32'; context.fillRect(0, 0, 32, 32)
    return canvas.toDataURL('image/png').split(',')[1]
  })
  return { name: 'fixture.png', mimeType: 'image/png', buffer: Buffer.from(encoded, 'base64') }
}
async function setup(page: Page, mode: 'normal' | 'lost' | 'denied' | 'unsafe' | 'foreign' | 'guest' = 'normal') {
  const calls = { reads: 0, uploads: 0 }
  let saved: string | null = null
  await page.route('https://images.example.test/**', (route) => route.fulfill({ status: 404 }))
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(mode === 'guest' ? { status: 401, json: { error: { message: 'Guest' } } } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'buyer', first_name: 'Buyer', role: 'customer', email: 'buyer@example.test' } })
    if (path.endsWith('/auth/logout')) return route.fulfill({ status: 204 })
    if (path === '/api/v1/me') { calls.reads++; return route.fulfill({ json: { id: mode === 'foreign' ? 'other-owner' : 'buyer', avatar_url: saved } }) }
    if (path.endsWith('/me/avatar')) {
      calls.uploads++
      expect(req.method()).toBe('POST')
      expect(req.headers().authorization).toBe('Bearer fixture-token')
      expect(req.headers()['content-type']).toContain('multipart/form-data; boundary=')
      expect(req.postDataBuffer()!.toString('latin1')).toContain('name="avatar"; filename="fixture.png"')
      if (mode === 'denied') return route.fulfill({ status: 422, json: { error: { message: 'Image is corrupt or unsupported.' } } })
      saved = imageUrl
      if (mode === 'lost') return route.abort('failed')
      return route.fulfill({ json: { avatar_url: mode === 'unsafe' ? 'javascript:alert(1)' : imageUrl } })
    }
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  return calls
}
test('photo selection previews locally and explicit upload uses multipart', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto('/account')
  await page.getByRole('link', { name: 'Manage your profile photo', exact: true }).click()
  await expect(page.getByText('No profile photo saved.')).toBeVisible()
  const file = await picture(page)
  await page.getByLabel('Choose profile photo', { exact: true }).setInputFiles(file)
  await expect(page.getByRole('img', { name: 'Selected profile photo preview' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Upload selected photo' })).toBeEnabled()
  expect(calls.uploads).toBe(0)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('profile-photo.png'), fullPage: true })
  await page.getByRole('button', { name: 'Upload selected photo' }).click()
  await expect(page.getByText('Profile photo uploaded. Refreshing the saved photo.')).toBeVisible()
  await expect(page.getByText('The saved photo could not be displayed.')).toBeVisible()
  await expect(page.getByRole('img', { name: 'Selected profile photo preview' })).not.toBeVisible()
  expect(calls.uploads).toBe(1)
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))).not.toMatch(/fixture.png|blob:|images.example.test/)
})
test('discard and refresh clear local selections without uploading', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/account/photo')
  const file = await picture(page)
  await page.getByLabel('Choose profile photo', { exact: true }).setInputFiles(file)
  await expect(page.getByRole('button', { name: 'Upload selected photo' })).toBeEnabled()
  await page.getByRole('button', { name: 'Discard selected photo' }).click()
  await expect(page.getByRole('button', { name: 'Upload selected photo' })).toBeDisabled()
  await page.getByLabel('Choose profile photo', { exact: true }).setInputFiles(file)
  await expect(page.getByRole('button', { name: 'Upload selected photo' })).toBeEnabled()
  await page.getByRole('button', { name: 'Refresh saved photo' }).click()
  await expect(page.getByRole('button', { name: 'Upload selected photo' })).toBeDisabled()
  await expect(page.getByRole('img', { name: 'Selected profile photo preview' })).not.toBeVisible()
  expect(calls.uploads).toBe(0)
})
test('unsupported, oversized and corrupt selections never upload', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/account/photo')
  const input = page.getByLabel('Choose profile photo', { exact: true })
  await input.setInputFiles({ name: 'bad.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg/>') })
  await expect(page.getByRole('alert')).toContainText('Choose a JPEG')
  await input.setInputFiles({ name: 'large.png', mimeType: 'image/png', buffer: Buffer.alloc(2 * 1024 * 1024 + 1) })
  await expect(page.getByRole('alert')).toContainText('2 MiB')
  await input.setInputFiles({ name: 'corrupt.png', mimeType: 'image/png', buffer: Buffer.from('not an image') })
  await expect(page.getByRole('alert')).toContainText('could not be decoded')
  await expect(page.getByRole('button', { name: 'Upload selected photo' })).toBeDisabled()
  expect(calls.uploads).toBe(0)
})
for (const mode of ['lost', 'unsafe'] as const) test(`${mode} upload response locks repeats even after refresh`, async ({ page }) => {
  const calls = await setup(page, mode)
  await page.goto('/account/photo')
  await page.getByLabel('Choose profile photo', { exact: true }).setInputFiles(await picture(page))
  await page.getByRole('button', { name: 'Upload selected photo' }).click()
  await expect(page.getByText('Further changes are locked', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Refresh saved photo' }).click()
  await expect(page.getByLabel('Choose profile photo', { exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Upload selected photo' })).toBeDisabled()
  expect(calls.uploads).toBe(1)
})
test('definite upload rejection does not replace the saved image or claim success', async ({ page }) => {
  const calls = await setup(page, 'denied')
  await page.goto('/account/photo')
  await page.getByLabel('Choose profile photo', { exact: true }).setInputFiles(await picture(page))
  await page.getByRole('button', { name: 'Upload selected photo' }).click()
  await expect(page.getByRole('alert')).toContainText('Image is corrupt or unsupported.')
  await expect(page.getByText('No profile photo saved.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Upload selected photo' })).toBeEnabled()
  expect(calls.uploads).toBe(1)
})
test('foreign photo responses cannot be displayed or replaced', async ({ page }) => {
  await setup(page, 'foreign')
  await page.goto('/account/photo')
  await expect(page.getByRole('alert')).toContainText('could not be verified for this account')
  await expect(page.getByLabel('Choose profile photo', { exact: true })).not.toBeVisible()
})
test('guests never read private photo data', async ({ page }) => {
  const calls = await setup(page, 'guest')
  await page.goto('/account/photo')
  await expect(page.getByText('Sign in to manage your account.')).toBeVisible()
  expect(calls.reads).toBe(0)
  expect(calls.uploads).toBe(0)
})
