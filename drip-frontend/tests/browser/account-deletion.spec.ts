import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

async function setup(page: Page, mode = 'success', role = 'customer') {
  const writes: unknown[] = []
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (path.endsWith('/auth/refresh')) return route.fulfill(mode === 'guest' ? { status: 401, json: { error: { message: 'Not signed in' } } } : { json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'owner', email: 'buyer@example.test', role } })
    if (path.endsWith('/customers/me') && req.method() === 'DELETE') {
      expect(req.headers().authorization).toBe('Bearer fixture-token')
      writes.push(req.postDataJSON())
      if (mode === 'lost') return route.abort()
      if (mode === 'unexpected') return route.fulfill({ json: { success: true } })
      if (mode === 'blocked') return route.fulfill({ status: 422, json: { error: { message: 'Wait for pending refunds before deleting the account.' } } })
      return route.fulfill({ status: 204 })
    }
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  await page.goto('/account/delete')
  return writes
}
async function confirm(page: Page) {
  await page.getByLabel('Current password', { exact: true }).fill(' exact Password1 ')
  await page.getByLabel('Type DELETE MY ACCOUNT', { exact: true }).fill('DELETE MY ACCOUNT')
  await page.getByRole('checkbox').check()
}
test('explicit deletion confirms retention and clears the local session', async ({ page }, info) => {
  const writes = await setup(page)
  const submit = page.getByRole('button', { name: 'Permanently disable my account' })
  await expect(submit).toBeDisabled()
  await confirm(page)
  expect(writes).toHaveLength(0)
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))).not.toContain('exact Password1')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.screenshot({ path: info.outputPath('account-deletion.png'), fullPage: true })
  await submit.dblclick()
  await expect(page.getByRole('heading', { name: 'Account deletion confirmed' })).toBeVisible()
  expect(writes).toEqual([{ password: ' exact Password1 ', confirm_phrase: 'DELETE MY ACCOUNT' }])
  await page.getByRole('navigation', { name: 'Footer' }).getByRole('link', { name: 'Your account', exact: true }).click()
  await expect(page.getByRole('link', { name: /^Sign in/ }).first()).toBeVisible()
})
test('incorrect phrase and cleared confirmation never write', async ({ page }) => {
  const writes = await setup(page)
  await confirm(page)
  await page.getByLabel('Type DELETE MY ACCOUNT', { exact: true }).fill('delete my account')
  await expect(page.getByRole('button', { name: 'Permanently disable my account' })).toBeDisabled()
  await page.getByRole('button', { name: 'Clear confirmation' }).click()
  await expect(page.getByLabel('Current password', { exact: true })).toHaveValue('')
  await expect(page.getByRole('checkbox')).not.toBeChecked()
  expect(writes).toHaveLength(0)
})
test('known rejection displays the blocker and requires fresh confirmation', async ({ page }) => {
  const writes = await setup(page, 'blocked')
  await confirm(page)
  await page.getByRole('button', { name: 'Permanently disable my account' }).click()
  await expect(page.getByText('Wait for pending refunds before deleting the account.')).toBeVisible()
  await expect(page.getByLabel('Current password', { exact: true })).toHaveValue('')
  await expect(page.getByRole('button', { name: 'Permanently disable my account' })).toBeDisabled()
  expect(writes).toHaveLength(1)
})
for (const mode of ['lost', 'unexpected']) test(`${mode} outcome locks further deletion without claiming success`, async ({ page }) => {
  const writes = await setup(page, mode)
  await confirm(page)
  await page.getByRole('button', { name: 'Permanently disable my account' }).click()
  await expect(page.getByText(/Deletion could not be confirmed and may already have happened/)).toBeVisible()
  await expect(page.getByLabel('Current password', { exact: true })).toBeDisabled()
  await expect(page.getByRole('heading', { name: 'Account deletion confirmed' })).toHaveCount(0)
  expect(writes).toHaveLength(1)
})
for (const role of ['seller', 'admin']) test(`${role} cannot use customer offboarding`, async ({ page }) => {
  const writes = await setup(page, 'success', role)
  await expect(page.getByText(/require managed offboarding/)).toBeVisible()
  await expect(page.getByLabel('Current password', { exact: true })).toHaveCount(0)
  expect(writes).toHaveLength(0)
})
test('guests cannot submit deletion', async ({ page }) => {
  const writes = await setup(page, 'guest')
  await expect(page.getByText('Sign in to manage your account.')).toBeVisible()
  await expect(page.getByLabel('Current password', { exact: true })).toHaveCount(0)
  expect(writes).toHaveLength(0)
})
