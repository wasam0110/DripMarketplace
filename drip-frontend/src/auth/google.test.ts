import { expect, it } from 'vitest'
import { googleAuthorizationUrl } from './google'

it('allows the exact Google authorization endpoint', () => {
  const url = 'https://accounts.google.com/o/oauth2/v2/auth?state=fixture&response_type=code'
  expect(googleAuthorizationUrl(url)).toBe(url)
})
it.each([
  null, {}, '/auth/google', 'http://accounts.google.com/o/oauth2/v2/auth',
  'https://accounts.google.com.evil.test/o/oauth2/v2/auth',
  'https://accounts.google.com:8443/o/oauth2/v2/auth',
  'https://user:password@accounts.google.com/o/oauth2/v2/auth',
  'https://accounts.google.com/unexpected',
  'https://accounts.google.com/o/oauth2/v2/auth#token',
])('rejects unexpected authorization address %s', (value) => {
  expect(() => googleAuthorizationUrl(value)).toThrow()
})
