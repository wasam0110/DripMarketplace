import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

async function setup(page: Page, mode: 'ready' | 'lost' | 'mismatch' | 'rejected' | 'unavailable' = 'ready', role = 'seller', verified = true) {
  let profile = { id: '11111111-1111-4111-8111-111111111111', brand_name: 'Fixture Label', description: 'Original brand story.', return_policy: 'Original return policy.', whatsapp_number: '03001234567', instagram_handle: 'fixture_label', brand_color: '#203C32' }
  const writes: Record<string, unknown>[] = []
  const sellerCalls: string[] = []
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    const method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'anonymous'
      ? { status: 401, json: { error: { message: 'No session' } } } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, email: 'seller@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.endsWith('/cart')) return route.fulfill({ json: { items: [], item_count: 0, subtotal: '0', shipping_fee: '0', total: '0' } })
    if (path.includes('/seller/')) sellerCalls.push(`${method} ${path}`)
    if (path.endsWith('/seller/me')) {
      if (method === 'PATCH') {
        const patch = route.request().postDataJSON()
        writes.push(patch)
        if (mode === 'rejected') return route.fulfill({ status: 422, json: { error: { message: 'Profile validation failed' } } })
        if (mode === 'mismatch') return route.fulfill({ json: profile })
        profile = { ...profile, ...patch }
        if (mode === 'lost') return route.abort()
        await new Promise((resolve) => setTimeout(resolve, 150))
      }
      return route.fulfill(mode === 'unavailable' ? { status: 403, json: { error: { message: 'Seller profile unavailable' } } } : { json: profile })
    }
    return route.fulfill({ status: 404, json: { error: { message: 'Unexpected API call' } } })
  })
  return { writes, sellerCalls }
}

test('edits only allowed changes, confirms save and clears optional text', async ({ page }, info) => {
  const state = await setup(page)
  await page.goto('/seller/profile')
  await expect(page.getByLabel('Brand description')).toHaveValue('Original brand story.')
  await expect(page.getByRole('button', { name: 'Save brand profile', exact: true })).toBeDisabled()
  await page.getByLabel('Brand description').fill('Updated label story.')
  await page.getByLabel('Instagram handle').fill('')
  await page.getByLabel('Brand colour', { exact: true }).fill('#AABBCC')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.getByRole('heading', { level: 1 }).click()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('seller-profile.png'), fullPage: true })
  await page.getByRole('button', { name: 'Save brand profile', exact: true }).dblclick()
  await expect(page.getByText('Brand profile saved.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Brand description')).toHaveValue('Updated label story.')
  expect(state.writes).toEqual([{ description: 'Updated label story.', instagram_handle: '', brand_color: '#AABBCC' }])
  expect(state.sellerCalls.every((call) => ['GET /api/v1/seller/me', 'PATCH /api/v1/seller/me'].includes(call))).toBe(true)
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain('Updated label story.')
})

test('discard and refresh never write a draft', async ({ page }) => {
  const state = await setup(page)
  await page.goto('/seller/profile')
  await page.getByLabel('Brand description').fill('Unsent draft')
  await page.getByRole('button', { name: 'Discard brand changes' }).click()
  await expect(page.getByLabel('Brand description')).toHaveValue('Original brand story.')
  await page.getByLabel('Brand description').fill('Another unsent draft')
  await page.getByRole('button', { name: 'Refresh brand profile' }).click()
  await expect(page.getByLabel('Brand description')).toHaveValue('Original brand story.')
  expect(state.writes).toEqual([])
})

for (const mode of ['lost', 'mismatch'] as const) test(`${mode} save locks writes, refresh only inspects`, async ({ page }) => {
  const state = await setup(page, mode)
  await page.goto('/seller/profile')
  await page.getByLabel('Brand description').fill('Possibly saved story')
  await page.getByRole('button', { name: 'Save brand profile', exact: true }).click()
  await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await expect(page.getByText('Brand profile saved.', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Refresh brand profile' }).click()
  await expect(page.getByLabel('Brand description')).toHaveValue(mode === 'lost' ? 'Possibly saved story' : 'Original brand story.')
  await expect(page.getByLabel('Brand description')).toBeDisabled()
  expect(state.writes).toHaveLength(1)
})

test('422 remains editable without automatic replay', async ({ page }) => {
  const state = await setup(page, 'rejected')
  await page.goto('/seller/profile')
  await page.getByLabel('Brand description').fill('Rejected draft')
  await page.getByRole('button', { name: 'Save brand profile', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Profile validation failed')
  await expect(page.getByLabel('Brand description')).toBeEnabled()
  expect(state.writes).toHaveLength(1)
})

test('failed profile read never creates an editable empty form', async ({ page }) => {
  const state = await setup(page, 'unavailable')
  await page.goto('/seller/profile')
  await expect(page.getByRole('alert')).toContainText('Seller profile unavailable')
  await expect(page.getByLabel('Brand description')).toHaveCount(0)
  expect(state.writes).toEqual([])
})

for (const [role, verified] of [['anonymous', true], ['customer', true], ['admin', true], ['seller', false]] as const) test(`${role}, verified=${verified} cannot read or edit brand profile`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified)
  await page.goto('/seller/profile')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(role === 'anonymous' ? 'Sign in to manage your brand' : role !== 'seller' ? 'A seller account is required' : 'Verify your email first')
  await expect(page.getByLabel('Brand description')).toHaveCount(0)
  expect(state.sellerCalls).toEqual([])
})
