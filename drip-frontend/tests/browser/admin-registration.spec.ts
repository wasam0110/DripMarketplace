import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const seller = '11111111-1111-4111-8111-111111111111', admin = '44444444-4444-4444-8444-444444444444', other = '55555555-5555-4555-8555-555555555555'
async function setup(page: Page, mode = 'ready', role = 'admin', verified = true) {
  let status = mode === 'zero' ? 'pending_approval' : mode === 'recorded' ? 'active' : 'pending_payment', fee = mode === 'zero' ? '0.00' : '5000.25'
  let paid: string | null = mode === 'recorded' ? '2026-10-28T12:00:00Z' : null, reference: string | null = mode === 'recorded' ? 'SAVED-REF' : mode === 'partial' ? 'LEGACY-REF' : null, actor: string | null = paid ? other : null
  const writes: { path: string; body: unknown }[] = []
  const detail = () => ({ id: seller, brand_name: 'Fixture Label', status, slots_used: 1, total_slots: 50, product_count: 1, total_gmv: '1000.25', platform_cut: '150.03', available_balance: '500.25', joined_at: '2026-10-28T10:00:00Z', slug: 'fixture-label', description: 'Independent everyday clothing.', whatsapp_number: null, instagram_handle: null, logo_url: null, return_policy: 'Seven-day returns.', pending_balance: '200.00', registration_fee: fee, rejected_reason: null, registration_amount_due: status === 'pending_payment' && !paid ? fee : '0.00', registration_paid_at: paid, registration_payment_reference: reference, registration_paid_by: actor })
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: admin, role, email: 'admin@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.includes('/admin/sellers/')) {
      expect(route.request().headers().authorization).toBe('Bearer fixture-token')
      if (method === 'POST') {
        const body = route.request().postDataJSON(); writes.push({ path, body })
        if (mode === 'rejection') return route.fulfill({ status: 422, json: { error: { message: 'Payment no longer matches the amount due.' } } })
        expect(path).toBe(`/api/v1/admin/sellers/${seller}/registration-payment`)
        status = mode === 'advanced' ? 'active' : 'pending_approval'; paid = '2026-10-28T12:00:00Z'; reference = mode === 'wrong-reference' ? 'OTHER-REF' : body.reference; actor = mode === 'wrong-actor' ? other : admin
        if (mode === 'wrong-amount') fee = '5000.26'
        if (mode === 'lost') return route.abort()
        return route.fulfill({ json: { status } })
      }
      if (mode === 'denied' || (mode === 'readback-denied' && writes.length)) return route.fulfill({ status: 403, json: { error: { message: 'Receipt unavailable' } } })
      return route.fulfill({ json: { ...detail(), ...(mode === 'missing-fields' ? { registration_amount_due: undefined } : {}) } })
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return { writes, change: (kind: string) => { if (kind === 'amount') fee = '6000.25'; if (kind === 'status') status = 'rejected'; if (kind === 'receipt') { paid = '2026-10-28T12:00:00Z'; actor = other; reference = 'OTHER-REF'; status = 'pending_approval' } } }
}
const open = (page: Page) => page.goto(`/admin/sellers/${seller}`)
async function review(page: Page) {
  await page.getByLabel('Received registration amount (PKR)', { exact: true }).fill('5000.25')
  await page.getByLabel('Registration transfer reference', { exact: true }).fill('  BANK-123  ')
  await page.getByLabel('I verified this transfer in the receiving account', { exact: true }).check()
  await page.getByRole('button', { name: 'Review registration payment', exact: true }).click()
}
test('records one reviewed transfer, displays exact receipt and keeps approval separate', async ({ page }, info) => {
  const duplicateKeys: string[] = []
  page.on('console', (message) => { if (message.text().includes('same key')) duplicateKeys.push(message.text()) })
  const state = await setup(page); await open(page); await review(page); expect(state.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('registration-payment-review.png'), fullPage: true })
  await page.getByRole('button', { name: 'Confirm registration payment', exact: true }).dblclick()
  await expect(page.getByText('Registration payment saved and confirmed. Seller approval is separate.', { exact: true })).toBeVisible()
  await expect(page.getByText('Awaiting approval', { exact: true })).toBeVisible(); await expect(page.getByText('BANK-123', { exact: true })).toBeVisible(); await expect(page.getByText(admin, { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Review registration payment', exact: true })).toHaveCount(0)
  expect(state.writes).toEqual([{ path: `/api/v1/admin/sellers/${seller}/registration-payment`, body: { amount: '5000.25', reference: 'BANK-123' } }])
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toMatch(/BANK-123|5000\.25|fixture-token/)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('registration-receipt.png'), fullPage: true })
  expect(duplicateKeys).toEqual([])
})
test('checkbox, exact amount and usable reference are mandatory; back does not submit', async ({ page }) => {
  const state = await setup(page); await open(page); await page.getByRole('button', { name: 'Review registration payment', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('Verify the transfer')
  await page.getByLabel('I verified this transfer in the receiving account', { exact: true }).check(); await page.getByLabel('Received registration amount (PKR)', { exact: true }).fill('5000.251'); await page.getByRole('button', { name: 'Review registration payment', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('exact outstanding')
  await page.getByLabel('Received registration amount (PKR)', { exact: true }).fill('5000.25'); await page.getByLabel('Registration transfer reference', { exact: true }).fill('   '); await page.getByRole('button', { name: 'Review registration payment', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('transfer reference')
  await review(page); await page.getByRole('button', { name: 'Back to payment edits', exact: true }).click(); expect(state.writes).toEqual([])
})
for (const kind of ['amount', 'status', 'receipt']) test(`preflight catches changed ${kind} without POST`, async ({ page }) => {
  const state = await setup(page); await open(page); await review(page); state.change(kind); await page.getByRole('button', { name: 'Confirm registration payment', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('changed'); expect(state.writes).toEqual([])
})
for (const mode of ['lost', 'wrong-reference', 'wrong-actor', 'wrong-amount', 'readback-denied']) test(`${mode} locks both payment and seller decisions across reload`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm registration payment', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); await expect(page.getByText('Registration payment saved and confirmed. Seller approval is separate.', { exact: true })).toHaveCount(0)
  await page.reload(); await expect(page.getByText(/A seller update is awaiting confirmation/)).toBeVisible(); const button = page.getByRole('button', { name: 'Review seller decision', exact: true }); if (await button.count()) await expect(button).toBeDisabled(); expect(state.writes).toHaveLength(1)
})
test('known rejection permits corrections without replay', async ({ page }) => {
  const state = await setup(page, 'rejection'); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm registration payment', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('no longer matches'); await expect(page.getByRole('button', { name: 'Back to payment edits', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['zero', 'partial', 'recorded', 'missing-fields', 'denied']) test(`${mode} never enables a new payment record`, async ({ page }) => {
  const state = await setup(page, mode); await open(page)
  const message = mode === 'zero' ? 'No registration fee was quoted; no paid receipt is recorded.' : mode === 'partial' ? 'Registration payment metadata is incomplete.' : mode === 'recorded' ? 'SAVED-REF' : mode === 'denied' ? 'Receipt unavailable' : 'could not be verified'
  await expect(page.getByText(message, { exact: mode === 'zero' || mode === 'recorded' || mode === 'denied' }).first()).toBeVisible(); await expect(page.getByRole('button', { name: 'Review registration payment', exact: true })).toHaveCount(0); expect(state.writes).toEqual([])
})
test('a separate later approval does not invalidate the matching receipt', async ({ page }) => {
  const state = await setup(page, 'advanced'); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm registration payment', exact: true }).click(); await expect(page.getByText('Registration payment saved and confirmed. Seller approval is separate.', { exact: true })).toBeVisible(); await expect(page.getByText('Active', { exact: true })).toBeVisible(); expect(state.writes).toHaveLength(1)
})
for (const [role, verified] of [['seller', true], ['customer', true], ['admin', false]] as const) test(`${role} verified=${verified} has no payment action`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { level: 1 })).toHaveText(role === 'admin' ? 'Verify your email first' : 'An administrator account is required'); await expect(page.getByRole('button', { name: 'Review registration payment', exact: true })).toHaveCount(0); expect(state.writes).toEqual([])
})
