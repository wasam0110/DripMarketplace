import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const id = '11111111-1111-4111-8111-111111111111'
const second = '22222222-2222-4222-8222-222222222222'
const home = { id, label: 'Home', street: '123 Example Road', city: 'Karachi', province: 'Sindh', is_default: true }
async function setup(page: Page, mode: 'normal' | 'guest' | 'foreign' | 'lost' | 'denied' | 'read-error' | 'limit' = 'normal') {
  const calls = { reads: 0, writes: [] as { path: string; method: string; body: unknown }[] }
  let profile = { id: 'buyer', first_name: 'Sara', last_name: null, phone: null, email: 'sara@example.test', has_verified_email: true }
  let addresses = mode === 'limit' ? Array.from({ length: 10 }, (_, i) => ({ ...home, id: `11111111-1111-4111-8111-${String(i).padStart(12, '0')}`, label: `Place ${i}`, is_default: i === 0 })) : [home]
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request(), path = new URL(req.url()).pathname, method = req.method()
    if (path.endsWith('/auth/refresh')) return mode === 'guest' ? route.fulfill({ status: 401, json: { error: { message: 'Guest' } } }) : route.fulfill({ json: { access_token: 'fixture-token' } })
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { ...profile, role: 'customer' } })
    if (path.endsWith('/auth/logout')) return route.fulfill({ status: 204 })
    if (path === '/api/v1/me' || path.includes('/me/addresses')) {
      expect(req.headers().authorization).toBe('Bearer fixture-token')
      if (method === 'GET') {
        calls.reads++
        if (mode === 'read-error') return route.fulfill({ status: 503, json: { error: { message: 'Account service unavailable.' } } })
        return route.fulfill({ json: path.endsWith('/addresses') ? addresses : { ...profile, id: mode === 'foreign' ? 'another-owner' : profile.id } })
      }
      const body = req.postData() ? req.postDataJSON() : null
      calls.writes.push({ path, method, body })
      if (mode === 'lost') return route.abort('failed')
      if (mode === 'denied') return route.fulfill({ status: 403, json: { error: { message: 'Account change denied.' } } })
      if (path === '/api/v1/me') { profile = { ...profile, ...body }; return route.fulfill({ json: profile }) }
      if (path.endsWith('/set-default')) {
        const target = path.split('/').at(-2)
        addresses = addresses.map((a) => ({ ...a, is_default: a.id === target }))
        return route.fulfill({ json: addresses.find((a) => a.id === target) })
      }
      if (method === 'DELETE') { addresses = addresses.filter((a) => !path.endsWith(a.id)); return route.fulfill({ status: 204 }) }
      expect(body).not.toHaveProperty('id')
      const result = { ...body, id: method === 'POST' ? second : path.split('/').at(-1) }
      addresses = addresses.filter((a) => a.id !== result.id).map((a) => result.is_default ? { ...a, is_default: false } : a).concat(result)
      return route.fulfill({ status: method === 'POST' ? 201 : 200, json: result })
    }
    return route.fulfill({ json: { items: [], total: 0 } })
  })
  return calls
}
async function fillAddress(page: Page) {
  await page.getByLabel('Address label', { exact: true }).fill('Office')
  await page.getByLabel('Street address', { exact: true }).fill('456 Example Street')
  await page.getByLabel('City', { exact: true }).fill('Lahore')
  await page.getByLabel('Province', { exact: true }).fill('Punjab')
}
test('profile updates changed fields only and refreshes the account greeting', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto('/account/profile')
  await expect(page.getByLabel('First name', { exact: true })).toHaveValue('Sara')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.screenshot({ path: info.outputPath('profile.png'), fullPage: true })
  await page.getByLabel('First name', { exact: true }).fill('Ayesha')
  await page.getByRole('button', { name: 'Save profile' }).click()
  await expect(page.getByText('Profile updated.', { exact: true })).toBeVisible()
  expect(calls.writes).toEqual([{ path: '/api/v1/me', method: 'PATCH', body: { first_name: 'Ayesha' } }])
  await page.getByRole('link', { name: 'Back to account' }).click()
  await expect(page.getByRole('heading', { name: 'Welcome, Ayesha.' })).toBeVisible()
})
test('profile validation prevents silent clearing and invalid phone writes', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/account/profile')
  await page.getByLabel('First name', { exact: true }).fill('')
  await page.getByRole('button', { name: 'Save profile' }).click()
  await expect(page.getByRole('alert')).toContainText('cannot clear')
  await page.getByLabel('First name', { exact: true }).fill('Sara')
  await page.getByLabel('Mobile number', { exact: true }).fill('123')
  await page.getByRole('button', { name: 'Save profile' }).click()
  await expect(page.getByRole('alert')).toContainText('Pakistani mobile')
  expect(calls.writes).toEqual([])
})
test('addresses support create, edit, default selection and confirmed deletion', async ({ page }, info) => {
  const calls = await setup(page)
  await page.goto('/account/addresses')
  await page.getByRole('button', { name: 'Add address', exact: true }).click()
  await fillAddress(page)
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.locator('body').evaluate((body) => body.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('addresses.png'), fullPage: true })
  await page.getByRole('button', { name: 'Save address', exact: true }).click()
  await expect(page.getByText('Address added.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Edit Office', exact: true }).click()
  await page.getByLabel('Street address', { exact: true }).fill('789 Updated Street')
  await page.getByRole('button', { name: 'Save address', exact: true }).click()
  await expect(page.getByText('Address updated.', { exact: true })).toBeVisible()
  await expect(page.getByText('789 Updated Street', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Make Office default', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Office · Default' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Home · Default' })).not.toBeVisible()
  await page.getByRole('button', { name: 'Delete Office', exact: true }).click()
  await page.getByRole('button', { name: 'Keep address', exact: true }).click()
  expect(calls.writes).toHaveLength(3)
  await page.getByRole('button', { name: 'Delete Office', exact: true }).click()
  await page.getByRole('button', { name: 'Yes, delete address', exact: true }).click()
  await expect(page.getByText('Address deleted.', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Office · Default' })).not.toBeVisible()
  expect(calls.writes.map((call) => call.method)).toEqual(['POST', 'PATCH', 'POST', 'DELETE'])
})
test('lost address creation blocks duplicate writes even after refresh', async ({ page }) => {
  const calls = await setup(page, 'lost')
  await page.goto('/account/addresses')
  await page.getByRole('button', { name: 'Add address', exact: true }).click()
  await fillAddress(page)
  await page.getByRole('button', { name: 'Save address', exact: true }).click()
  await expect(page.getByText('Further changes are locked', { exact: false })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Save address', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Refresh addresses', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Add address', exact: true })).toBeDisabled()
  expect(calls.writes).toHaveLength(1)
})
test('foreign profile information is hidden and cannot be edited', async ({ page }) => {
  await setup(page, 'foreign')
  await page.goto('/account/profile')
  await expect(page.getByRole('alert')).toContainText('could not be verified')
  await expect(page.getByLabel('First name', { exact: true })).not.toBeVisible()
  await expect(page.getByText('sara@example.test', { exact: false })).not.toBeVisible()
})
test('guests make no private profile or address reads', async ({ page }) => {
  const calls = await setup(page, 'guest')
  for (const path of ['/account/profile', '/account/addresses']) {
    await page.goto(path)
    await expect(page.getByText('Sign in to manage your account.')).toBeVisible()
  }
  expect(calls.reads).toBe(0)
})
test('address limit hides creation and read failures hide writes', async ({ page }) => {
  await setup(page, 'limit')
  await page.goto('/account/addresses')
  await expect(page.getByText('You have reached the ten-address limit.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Add address', exact: true })).not.toBeVisible()
  await page.route('**/me/addresses', (route) => route.fulfill({ status: 503, json: { error: { message: 'Account service unavailable.' } } }))
  await page.getByRole('button', { name: 'Refresh addresses', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Account service unavailable.')
  await expect(page.getByRole('button', { name: 'Edit Place 0', exact: true })).not.toBeVisible()
})
test('definite profile rejection retains the draft without claiming success', async ({ page }) => {
  const calls = await setup(page, 'denied')
  await page.goto('/account/profile')
  await page.getByLabel('First name', { exact: true }).fill('Ayesha')
  await page.getByRole('button', { name: 'Save profile' }).click()
  await expect(page.getByRole('alert')).toContainText('Account change denied.')
  await expect(page.getByLabel('First name', { exact: true })).toHaveValue('Ayesha')
  await expect(page.getByRole('button', { name: 'Save profile' })).toBeEnabled()
  expect(calls.writes).toHaveLength(1)
})

test('lost profile updates stay locked after a read refresh', async ({ page }) => {
  const calls = await setup(page, 'lost')
  await page.goto('/account/profile')
  await page.getByLabel('First name', { exact: true }).fill('Ayesha')
  await page.getByRole('button', { name: 'Save profile' }).click()
  await expect(page.getByText('Further changes are locked', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Refresh profile' }).click()
  await expect(page.getByLabel('First name', { exact: true })).toHaveValue('Sara')
  await expect(page.getByRole('button', { name: 'Save profile' })).toBeDisabled()
  expect(calls.writes).toHaveLength(1)
})

test('sign-out discards private profile drafts before back navigation', async ({ page }) => {
  const calls = await setup(page)
  await page.goto('/account/profile')
  await page.getByLabel('First name', { exact: true }).fill('Private Draft')
  await page.getByRole('link', { name: 'Back to account' }).click()
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Sign out', exact: true })).not.toBeVisible()
  const reads = calls.reads
  await page.goBack()
  await expect(page.getByText('Sign in to manage your account.')).toBeVisible()
  await expect(page.getByLabel('First name', { exact: true })).not.toBeVisible()
  expect(calls.reads).toBe(reads)
  expect(calls.writes).toEqual([])
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))).not.toMatch(/Private Draft|Example Road|sara@example/)
})
