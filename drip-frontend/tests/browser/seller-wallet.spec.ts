import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
const seller = '11111111-1111-4111-8111-111111111111', bankId = '22222222-2222-4222-8222-222222222222', payoutId = '33333333-3333-4333-8333-333333333333'
async function setup(page: Page, mode = 'ready', role = 'seller', verified = true) {
  let balance = '5000.25', min = '750', accountNumber = 'PK00TEST1234'
  let accounts = mode === 'no-bank' ? [] : [{ id: bankId, bank_name: 'Test Bank', account_title: 'Test Brand', account_number: accountNumber, is_default: true, created_at: '2026-10-28T10:00:00Z' }]
  const writes: { path: string; method: string; body: Record<string, unknown> | null }[] = [], reads: string[] = []
  const summary = () => ({ available_balance: balance, pending_balance: '1000.00', total_earned: '8000.00', total_commission: '800.00', minimum_withdrawal_amount: min, maximum_withdrawal_amount: '3000' })
  const payout = () => ({ id: payoutId, amount: '750.25', payment_method: 'bank_transfer', payment_detail: 'Test Bank — PK00TEST1234', status: 'requested', admin_note: null, requested_at: '2026-10-28T10:00:00Z', completed_at: null, transfer_reference: null })
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url()), path = url.pathname, method = route.request().method()
    if (path.endsWith('/auth/refresh')) return route.fulfill(role === 'guest' ? { status: 401, json: {} } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', role, email: 'seller@example.test', first_name: 'Ayesha', last_name: 'Khan', has_verified_email: verified } })
    if (path.includes('/seller/')) reads.push(`${method} ${path}${url.search}`)
    if (path.endsWith('/seller/me')) return route.fulfill({ json: { id: seller, brand_name: 'Fixture Label', status: mode === 'inactive' ? 'suspended' : 'active', registration_amount_due: '0.00', registration_paid_at: null } })
    if (path.includes('/seller/wallet') || path.includes('/seller/bank-accounts')) {
      if (method !== 'GET') {
        const body = method === 'DELETE' ? null : route.request().postDataJSON(); writes.push({ path, method, body })
        expect(route.request().headers().authorization).toBe('Bearer fixture-token')
        if (mode === 'lost') return route.abort()
        if (mode === 'rejected') return route.fulfill({ status: 400, json: { error: { message: 'Insufficient balance' } } })
        if (path.endsWith('/withdraw')) {
          balance = '4250.00'
          return route.fulfill({ status: 201, json: mode === 'mismatch' ? { ...payout(), amount: '900.00' } : payout() })
        }
        if (method === 'POST') {
          const added = { id: payoutId, created_at: '2026-10-28T10:00:00Z', ...body } as typeof accounts[number]
          accounts = [...accounts.map((a) => ({ ...a, is_default: body!.is_default ? false : a.is_default })), added]
          return route.fulfill({ status: 201, json: added })
        }
        accounts = accounts.filter((a) => !path.endsWith(a.id)); return route.fulfill({ status: 204 })
      }
      if (mode === 'denied' || (mode === 'read-denied' && writes.length && path.includes('/bank-accounts'))) return route.fulfill({ status: 403, json: { error: { message: 'Wallet unavailable' } } })
      if (path.endsWith('/wallet')) return route.fulfill({ json: mode === 'missing-limits' ? { ...summary(), minimum_withdrawal_amount: undefined } : summary() })
      if (path.endsWith('/bank-accounts')) return route.fulfill({ json: accounts.map((a) => a.id === bankId ? { ...a, account_number: accountNumber } : a) })
      const p = Number(url.searchParams.get('page') || 1)
      if (path.endsWith('/transactions')) {
        const type = url.searchParams.get('tx_type') || 'debit_withdrawal'
        return route.fulfill({ json: { data: [{ id: payoutId, type, amount: '750.25', balance_after: '4250.00', reference: payoutId, note: 'Test transaction', created_at: '2026-10-28T10:00:00Z' }], total: mode === 'pages' ? 26 : 1, page: p, per_page: 25, total_pages: mode === 'pages' ? 2 : 1 } })
      }
      if (path.endsWith('/payouts')) return route.fulfill({ json: { data: [{ ...payout(), status: url.searchParams.get('status') || 'completed', completed_at: '2026-10-28T12:00:00Z', transfer_reference: 'BANK-REF-001' }], total: 1, page: p, total_pages: 1 } })
    }
    return route.fulfill({ status: 404, json: {} })
  })
  return { writes, reads, reduceBalance: () => { balance = '500.00' }, changeLimits: () => { min = '1000' }, changeBank: () => { accountNumber = 'CHANGED9999' } }
}
const open = (page: Page) => page.goto('/seller/wallet')
async function review(page: Page) {
  await page.getByLabel('Payout amount (PKR)', { exact: true }).fill('750.25'); await page.getByLabel('Payout bank account', { exact: true }).selectOption(bankId)
  await page.getByRole('button', { name: 'Review payout request', exact: true }).click()
}
test('shows balances and configured limits then submits one reviewed payout', async ({ page }, info) => {
  const state = await setup(page); await open(page); await review(page); expect(state.writes).toEqual([])
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: info.outputPath('seller-wallet.png'), fullPage: true })
  await page.getByRole('button', { name: 'Confirm payout request', exact: true }).dblclick()
  await expect(page.getByText('Payout request recorded. Admin will process the transfer.', { exact: true })).toBeVisible()
  expect(state.writes).toEqual([{ path: '/api/v1/seller/wallet/withdraw', method: 'POST', body: { amount: '750.25', bank_account_id: bankId } }])
  await expect(page.getByRole('heading', { name: 'New payout request', exact: true })).toBeVisible()
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain('PK00TEST1234')
})
for (const mode of ['lost', 'mismatch']) test(`${mode} payout locks writes across reload`, async ({ page }) => {
  const state = await setup(page, mode); await open(page); await review(page)
  await page.getByRole('button', { name: 'Confirm payout request', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible()
  await page.reload(); await expect(page.getByText(/A wallet or bank-account change is awaiting confirmation/)).toBeVisible(); await expect(page.getByRole('button', { name: 'Review payout request', exact: true })).toBeDisabled(); expect(state.writes).toHaveLength(1)
})
test('known withdrawal rejection permits correction without replay', async ({ page }) => {
  const state = await setup(page, 'rejected'); await open(page); await review(page); await page.getByRole('button', { name: 'Confirm payout request', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Insufficient balance'); await expect(page.getByRole('button', { name: 'Back to payout edits', exact: true })).toBeEnabled(); expect(state.writes).toHaveLength(1)
})
for (const changed of ['balance', 'limits', 'bank']) test(`preflight catches changed ${changed} before POST`, async ({ page }) => {
  const state = await setup(page); await open(page); await review(page)
  if (changed === 'balance') state.reduceBalance(); else if (changed === 'limits') state.changeLimits(); else state.changeBank()
  await page.getByRole('button', { name: 'Confirm payout request', exact: true }).click(); await expect(page.getByRole('alert')).toBeVisible(); expect(state.writes).toEqual([])
  await expect(page.getByRole('button', { name: 'Review payout request', exact: true })).toBeEnabled()
})
test('invalid precision, amounts and backing out never submit', async ({ page }) => {
  const state = await setup(page); await open(page)
  await page.getByLabel('Payout bank account', { exact: true }).selectOption(bankId); await page.getByLabel('Payout amount (PKR)', { exact: true }).fill('749.99')
  await page.getByRole('button', { name: 'Review payout request', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('outside the current withdrawal limits')
  await review(page); await page.getByRole('button', { name: 'Back to payout edits', exact: true }).click(); expect(state.writes).toEqual([])
})
test('transaction and payout filters, pagination and transfer reference', async ({ page }) => {
  const state = await setup(page, 'pages'); await open(page); await page.getByRole('button', { name: 'Transactions', exact: true }).click()
  await page.getByRole('button', { name: 'Next page', exact: true }).click(); await expect(page.getByText('Page 2 of 2', { exact: true })).toBeVisible()
  await page.getByLabel('Transaction type', { exact: true }).selectOption('credit_refund'); await expect(page.getByText('Page 1 of 2', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Payout history', exact: true }).click(); await expect(page.getByText('Transfer reference: BANK-REF-001', { exact: true })).toBeVisible()
  await expect(page.getByText('Transfer destination: Hidden', { exact: true })).toBeVisible(); await page.getByRole('button', { name: 'Show transfer destination', exact: true }).click()
  await expect(page.getByText('Transfer destination: Test Bank — PK00TEST1234', { exact: true })).toBeVisible(); expect(state.writes).toEqual([])
})
async function bankReview(page: Page) {
  await page.getByRole('button', { name: 'Add bank account', exact: true }).click()
  await page.getByLabel('Bank name', { exact: true }).fill('New Bank'); await page.getByLabel('Account title (optional)', { exact: true }).fill('Brand Owner'); await page.getByLabel('Bank account number', { exact: true }).fill('PK00NEW5678')
  await page.getByRole('button', { name: 'Review bank account', exact: true }).click()
}
test('adds and removes a bank account after review and verifies readback', async ({ page }, info) => {
  const state = await setup(page); await page.goto('/seller/wallet/accounts'); await bankReview(page); expect(state.writes).toEqual([])
  await page.getByRole('button', { name: 'Confirm bank account', exact: true }).dblclick(); await expect(page.getByText('Payout bank account saved and confirmed.', { exact: true })).toBeVisible()
  await expect(page.getByText('Brand Owner · •••• 5678', { exact: true })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.getByRole('heading', { level: 1 }).click(); await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: info.outputPath('seller-bank-accounts.png'), fullPage: true })
  await page.getByRole('button', { name: 'Remove account •••• 5678', exact: true }).click(); expect(state.writes).toHaveLength(1)
  await page.getByRole('button', { name: 'Confirm account removal', exact: true }).click(); await expect(page.getByText('Payout bank account removal confirmed.', { exact: true })).toBeVisible()
  expect(state.writes.map((row) => row.method)).toEqual(['POST', 'DELETE'])
})
test('failed account readback locks further writes', async ({ page }) => {
  const state = await setup(page, 'read-denied'); await page.goto('/seller/wallet/accounts'); await bankReview(page)
  await page.getByRole('button', { name: 'Confirm bank account', exact: true }).click(); await expect(page.getByText(/Further changes are locked/)).toBeVisible(); expect(state.writes).toHaveLength(1)
})
for (const mode of ['denied', 'missing-limits', 'inactive', 'no-bank']) test(`${mode} prevents a payout request`, async ({ page }) => {
  await setup(page, mode); await open(page)
  await expect(page.getByText(mode === 'denied' ? 'Wallet unavailable' : mode === 'missing-limits' ? 'The wallet information could not be verified. Refresh to try again.' : mode === 'inactive' ? 'An active seller account is required to manage your wallet.' : 'Add a bank payout account before requesting a withdrawal.', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Review payout request', exact: true })).toHaveCount(0)
})
for (const [role, verified, heading] of [['guest', true, 'Sign in to manage your wallet'], ['customer', true, 'A seller account is required'], ['admin', true, 'A seller account is required'], ['seller', false, 'Verify your email first']] as const) test(`${role} verified=${verified} is gated`, async ({ page }) => {
  const state = await setup(page, 'ready', role, verified); await open(page); await expect(page.getByRole('heading', { name: heading })).toBeVisible(); expect(state.reads).toEqual([])
})
