import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const imageUrl = 'https://images.example.test/logo.webp'
async function picture(page: Page) {
  const encoded = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width = 48; canvas.height = 48
    const context = canvas.getContext('2d')!; context.fillStyle = '#203c32'; context.fillRect(0, 0, 48, 48)
    return canvas.toDataURL('image/png').split(',')[1]
  })
  return { name: 'logo-fixture.png', mimeType: 'image/png', buffer: Buffer.from(encoded, 'base64') }
}
async function setup(page: Page, mode = 'normal', role = 'seller', verified = true) {
  const calls = { reads: 0, uploads: 0 }
  let saved: string | null = null
  await page.route('https://images.example.test/**', (route) => route.fulfill({ status: 404 }))
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: { error: { message: 'No session' } } } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, first_name: 'Ayesha', email: 'seller@example.test', has_verified_email: verified } })
    if (path.endsWith('/seller/me')) {
      calls.reads++
      if (mode === 'unavailable') return route.fulfill({ status: 403, json: { error: { message: 'Seller unavailable' } } })
      return route.fulfill({ json: { id: mode === 'foreign' && calls.uploads ? '22222222-2222-4222-8222-222222222222' : '11111111-1111-4111-8111-111111111111', brand_name: 'Fixture Label', logo_url: saved } })
    }
    if (path.endsWith('/seller/logo')) {
      calls.uploads++
      expect(req.method()).toBe('POST')
      expect(req.headers().authorization).toBe('Bearer fixture-token')
      expect(req.headers()['content-type']).toContain('multipart/form-data; boundary=')
      expect(req.postDataBuffer()!.toString('latin1')).toContain('name="logo"; filename="logo-fixture.png"')
      if (mode === 'denied') return route.fulfill({ status: 422, json: { error: { message: 'Image is corrupt or unsupported.' } } })
      if (mode !== 'mismatch') saved = imageUrl
      if (mode === 'lost') return route.abort()
      await new Promise((resolve) => setTimeout(resolve, 100))
      return route.fulfill({ json: { logo_url: mode === 'unsafe' ? 'javascript:alert(1)' : imageUrl } })
    }
    if (path.endsWith('/cart')) return route.fulfill({ json: { items: [], item_count: 0, subtotal: '0', shipping_fee: '0', total: '0' } })
    return route.fulfill({ status: 404, json: { error: { message: 'Unexpected request' } } })
  })
  return calls
}
test('logo previews locally, uploads once and confirms the saved profile', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto('/seller/logo')
  await expect(page.getByText('No brand logo saved.')).toBeVisible()
  await page.getByLabel('Choose brand logo', { exact: true }).setInputFiles(await picture(page))
  await expect(page.getByRole('img', { name: 'Selected brand logo preview' })).toBeVisible()
  expect(calls.uploads).toBe(0)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.getByRole('heading', { level: 1 }).click()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('seller-logo.png'), fullPage: true })
  await page.getByRole('button', { name: 'Upload selected logo' }).dblclick()
  await expect(page.getByText('Brand logo saved and confirmed.', { exact: true })).toBeVisible()
  await expect(page.getByText('The saved logo could not be displayed.')).toBeVisible()
  await expect(page.getByRole('img', { name: 'Selected brand logo preview' })).toHaveCount(0)
  expect(calls.uploads).toBe(1)
  expect(calls.reads).toBeGreaterThanOrEqual(3)
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toMatch(/logo-fixture|blob:|images.example.test/)
})
test('discard and refresh never upload a selection', async ({ page }) => {
  const calls = await setup(page); await page.goto('/seller/logo')
  const file = await picture(page)
  await page.getByLabel('Choose brand logo', { exact: true }).setInputFiles(file)
  await expect(page.getByRole('button', { name: 'Upload selected logo' })).toBeEnabled()
  await page.getByRole('button', { name: 'Discard selected logo' }).click()
  await expect(page.getByRole('button', { name: 'Upload selected logo' })).toBeDisabled()
  await page.getByLabel('Choose brand logo', { exact: true }).setInputFiles(file)
  await expect(page.getByRole('button', { name: 'Upload selected logo' })).toBeEnabled()
  await page.getByRole('button', { name: 'Refresh saved logo' }).click()
  await expect(page.getByRole('img', { name: 'Selected brand logo preview' })).toHaveCount(0)
  expect(calls.uploads).toBe(0)
})
test('invalid, oversized and corrupt files are rejected locally', async ({ page }) => {
  const calls = await setup(page); await page.goto('/seller/logo')
  const input = page.getByLabel('Choose brand logo', { exact: true })
  await input.setInputFiles({ name: 'bad.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg/>') })
  await expect(page.getByRole('alert')).toContainText('Choose a JPEG')
  await input.setInputFiles({ name: 'large.png', mimeType: 'image/png', buffer: Buffer.alloc(2 * 1024 * 1024 + 1) })
  await expect(page.getByRole('alert')).toContainText('2 MiB')
  await input.setInputFiles({ name: 'bad.png', mimeType: 'image/png', buffer: Buffer.from('invalid') })
  await expect(page.getByRole('alert')).toContainText('could not be decoded')
  await expect(page.getByRole('button', { name: 'Upload selected logo' })).toBeDisabled()
  expect(calls.uploads).toBe(0)
})
for (const mode of ['lost', 'unsafe', 'mismatch', 'foreign']) test(`${mode} confirmation blocks repeated uploads`, async ({ page }) => {
  const calls = await setup(page, mode); await page.goto('/seller/logo')
  await page.getByLabel('Choose brand logo', { exact: true }).setInputFiles(await picture(page))
  await page.getByRole('button', { name: 'Upload selected logo' }).click()
  await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await expect(page.getByText('Brand logo saved and confirmed.', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Refresh saved logo' }).click()
  if (mode === 'foreign') {
    await expect(page.getByText(/The seller identity changed/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Upload selected logo' })).toHaveCount(0)
  } else await expect(page.getByRole('button', { name: 'Upload selected logo' })).toBeDisabled()
  expect(calls.uploads).toBe(1)
})
test('definite rejection preserves selection for explicit correction', async ({ page }) => {
  const calls = await setup(page, 'denied'); await page.goto('/seller/logo')
  await page.getByLabel('Choose brand logo', { exact: true }).setInputFiles(await picture(page))
  await page.getByRole('button', { name: 'Upload selected logo' }).click()
  await expect(page.getByRole('alert')).toContainText('corrupt or unsupported')
  await expect(page.getByText('No brand logo saved.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Upload selected logo' })).toBeEnabled()
  expect(calls.uploads).toBe(1)
})
for (const [role, verified] of [['guest', true], ['customer', true], ['admin', true], ['seller', false]] as const) test(`${role}, verified=${verified} cannot access logos`, async ({ page }) => {
  const calls = await setup(page, 'normal', role, verified); await page.goto('/seller/logo')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(role === 'guest' ? 'Sign in to manage your logo' : role !== 'seller' ? 'A seller account is required' : 'Verify your email first')
  expect(calls.reads).toBe(0); expect(calls.uploads).toBe(0)
})
test('failed profile read blocks image selection', async ({ page }) => {
  const calls = await setup(page, 'unavailable'); await page.goto('/seller/logo')
  await expect(page.getByRole('alert')).toContainText('Seller unavailable')
  await expect(page.getByLabel('Choose brand logo', { exact: true })).toHaveCount(0)
  expect(calls.uploads).toBe(0)
})
