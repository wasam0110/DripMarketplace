// Offline artifact QA only: no app server, application routes, or provider calls.
const { chromium } = require('../drip-frontend/node_modules/@playwright/test')
const path = require('node:path')
const { pathToFileURL } = require('node:url')

async function main() {
  const browser = await chromium.launch({ channel: 'msedge', headless: true })
  try {
    const context = await browser.newContext()
    const errors = [], external = []
    await context.route(/^https?:/, async (route) => {
      external.push(route.request().url())
      await route.abort()
    })
    const page = await context.newPage()
    page.on('pageerror', (error) => errors.push(error.message))
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto(pathToFileURL(path.resolve(__dirname, '../WearHowZ_Project_Audit_Handoff.html')).href)
    if (!(await page.title()).includes('Audit')) throw new Error('Unexpected title')
    const count = await page.locator('details.file').count()
    if (!count || !(await page.locator('#visible').innerText()).startsWith(String(count))) throw new Error('Missing inventory')
    if (!(await page.locator('section.warn').innerText()).includes('not a completed')) throw new Error('Missing review limitation')
    for (const id of ['latest-findings', 'auth-deep-review', 'customer-deep-review', 'start', 'coverage', 'excluded']) {
      if (await page.locator(`#${id}`).count() !== 1) throw new Error(`Missing section ${id}`)
    }
    await page.screenshot({ path: path.join(__dirname, 'handoff-desktop.png') })
    await page.locator('#filter').fill('drip-backend/app/services/auth_service.py')
    const found = page.locator('details.file:not([hidden])')
    if (await found.count() !== 1) throw new Error('Path search failed')
    await found.locator(':scope > summary').click()
    if (!await found.getAttribute('open') && await found.getAttribute('open') !== '') throw new Error('File details did not open')
    await page.locator('#filter').fill('no-such-file-audit-qa')
    if (await page.locator('details.file:not([hidden])').count()) throw new Error('Empty search failed')
    await page.locator('#filter').fill('')
    await page.setViewportSize({ width: 390, height: 844 })
    await page.evaluate(() => window.scrollTo(0, 0))
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)
    await page.screenshot({ path: path.join(__dirname, 'handoff-mobile.png') })
    if (overflow) throw new Error('Mobile horizontal overflow')
    if (errors.length || external.length) throw new Error(JSON.stringify({ errors, external }))
    console.log(JSON.stringify({ files: count, offline: true, consoleErrors: errors, externalRequests: external,
      filterAndDetails: 'passed', mobileHorizontalOverflow: false, screenshots: ['audit_tools/handoff-desktop.png', 'audit_tools/handoff-mobile.png'] }))
    await context.close()
  } finally {
    await browser.close()
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1 })
