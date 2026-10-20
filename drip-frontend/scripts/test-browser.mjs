import { spawnSync } from 'node:child_process'
import { mkdtempSync, realpathSync, rmSync } from 'node:fs'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import { basename, dirname, join } from 'node:path'

// Keep this project's run isolated from stale/shared Windows transform caches.
const require = createRequire(import.meta.url)
const temporaryRoot = realpathSync(tmpdir())
const cache = realpathSync(mkdtempSync(join(temporaryRoot, 'wearhowz-playwright-')))
try {
  const result = spawnSync(process.execPath, [
    require.resolve('@playwright/test/cli'), 'test', ...process.argv.slice(2),
  ], {
    stdio: 'inherit',
    env: { ...process.env, PWTEST_CACHE_DIR: cache },
  })
  if (result.error) console.error(result.error.message)
  process.exitCode = result.status ?? 1
} finally {
  // Delete only this invocation's verified, newly created temporary directory.
  if (dirname(cache) !== temporaryRoot || !basename(cache).startsWith('wearhowz-playwright-')) {
    throw new Error('Refusing to clean an unexpected browser-test cache path.')
  }
  rmSync(cache, { recursive: true, force: true })
}
