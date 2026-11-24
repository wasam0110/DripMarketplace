import { expect, it } from 'vitest'
const validCode = (value: string) => /^\d{6}$/.test(value.trim())
it('accepts only six-digit authenticator codes', () => {
  expect(validCode('123456')).toBe(true)
  for (const value of ['', '12345', '1234567', '12a456']) expect(validCode(value)).toBe(false)
})
