import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const owner = '22222222-2222-4222-8222-222222222222'
async function setup(page: Page, mode = 'ready', role = 'admin', verified = true) {
  let value = { commission_rate: 0.15, registration_fee: 5000, extra_slot_price: 50, free_shipping_threshold: 5000, standard_shipping_fee: 200, cod_timeout_minutes: 30, wallet_hold_days: 3 }
  const writes: Record<string, unknown>[] = [], reads: string[] = []
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: owner, role, email: 'admin@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (!path.endsWith('/admin/settings')) return route.fulfill({ json: { data: [], total: 0 } })
    if (route.request().method() === 'GET') {
      reads.push(path)
      if (mode === 'denied' || mode === 'readback-denied' && writes.length) return route.fulfill({ status: 403, json: { error: { message: 'Settings unavailable', code: 'FORBIDDEN' } } })
      return route.fulfill({ json: mode === 'malformed' ? { ...value, commission_rate: 2 } : value })
    }
    const body = route.request().postDataJSON(); writes.push(body)
    if (mode === 'lost') return route.abort('failed')
    if (mode === 'conflict') return route.fulfill({ status: 409, json: { error: { message: 'Settings changed during review', code: 'CONFLICT' } } })
    const { expected_settings: _, ...changes } = body
    value = { ...value, ...changes }
    return route.fulfill({ json: mode === 'wrong-receipt' ? { ...value, wallet_hold_days: 4 } : value })
  })
  return { writes, reads, change: () => { value.standard_shipping_fee = 250 } }
}
async function review(page: Page) {
  await page.getByLabel('Seller registration fee (PKR)', { exact: true }).fill('0')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Review settings changes' }).click()
  await expect(page.getByLabel('Confirm settings changes', { exact: true })).toBeFocused()
}
test('reviewed partial update verifies response and readback without duplicate writes', async ({ page }, info) => {
  const state = await setup(page); await page.goto('/admin/settings'); await review(page)
  await expect(page.getByText('5000 → 0', { exact: true })).toBeVisible()
  expect(state.writes).toHaveLength(0)
  await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('platform-settings-review.png'), fullPage: true })
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations).toEqual([])
  await page.getByRole('button', { name: 'Confirm settings update' }).dblclick()
  await expect(page.getByText('Platform settings saved and verified.', { exact: true })).toBeVisible()
  expect(state.writes).toHaveLength(1)
  expect(Object.keys(state.writes[0]).sort()).toEqual(['expected_settings', 'registration_fee'])
  expect(state.writes[0].expected_settings).toMatchObject({ registration_fee: 5000, commission_rate: 0.15 })
  await expect(page.getByLabel('Seller registration fee (PKR)', { exact: true })).toHaveValue('0')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
test('invalid and unchanged drafts send nothing', async ({ page }) => {
  const state = await setup(page); await page.goto('/admin/settings'); await page.getByRole('checkbox').check(); await page.getByRole('button', { name: 'Review settings changes' }).click(); await expect(page.getByRole('alert')).toContainText('Change at least one')
  await page.getByLabel('COD decision timeout (minutes)', { exact: true }).fill('4'); await page.getByRole('checkbox').check(); await page.getByRole('button', { name: 'Review settings changes' }).click(); await expect(page.getByRole('alert')).toContainText('valid cod decision')
  expect(state.writes).toHaveLength(0)
})
test('back and refresh discard the review without writing', async ({ page }) => { const state = await setup(page); await page.goto('/admin/settings'); await review(page); await page.getByRole('button', { name: 'Back to settings draft' }).click(); await expect(page.getByRole('button', { name: 'Confirm settings update' })).toHaveCount(0); await page.getByRole('button', { name: 'Refresh settings and discard draft' }).click(); await expect(page.getByLabel('Seller registration fee (PKR)', { exact: true })).toHaveValue('5000'); expect(state.writes).toHaveLength(0) })
test('stale preflight sends no settings', async ({ page }) => { const state = await setup(page); await page.goto('/admin/settings'); await review(page); state.change(); await page.getByRole('button', { name: 'Confirm settings update' }).click(); await expect(page.getByRole('alert')).toContainText('changed'); expect(state.writes).toHaveLength(0) })
for (const mode of ['lost', 'wrong-receipt', 'readback-denied']) test(`${mode} stays locked after reload`, async ({ page }) => { const state = await setup(page, mode); await page.goto('/admin/settings'); await review(page); await page.getByRole('button', { name: 'Confirm settings update' }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); await page.reload(); await expect(page.getByText(/A settings update is awaiting confirmation/)).toBeVisible(); expect(state.writes).toHaveLength(1); expect(await page.evaluate(() => JSON.stringify(sessionStorage))).not.toMatch(/registration_fee|fixture-token/) })
test('known server conflict permits fresh review without auto-retry', async ({ page }) => { const state = await setup(page, 'conflict'); await page.goto('/admin/settings'); await review(page); await page.getByRole('button', { name: 'Confirm settings update' }).click(); await expect(page.getByRole('alert')).toContainText('changed during review'); await expect(page.getByRole('button', { name: 'Review settings changes' })).toBeEnabled(); expect(state.writes).toHaveLength(1) })
for (const [role, verified] of [['customer', true], ['seller', true], ['guest', true], ['admin', false]] as const) test(`${role} verified=${verified} cannot read settings`, async ({ page }) => { const state = await setup(page, 'ready', role, verified); await page.goto('/admin/settings'); await expect(page.getByRole('heading', { level: 1 })).toContainText(role === 'guest' ? 'Sign in' : !verified ? 'Verify your email' : 'administrator'); expect(state.reads).toHaveLength(0) })
for (const mode of ['malformed', 'denied']) test(`${mode} settings fail closed`, async ({ page }) => { await setup(page, mode); await page.goto('/admin/settings'); await expect(page.getByRole('alert').first()).toBeVisible(); await expect(page.getByRole('button', { name: 'Review settings changes' })).toHaveCount(0) })
