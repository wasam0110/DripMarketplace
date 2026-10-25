import { expect, it } from 'vitest'
import { validatePasswordChange } from './password'
const valid = { current_password: 'OldPassword1', new_password: 'NewPassword2', confirm_password: 'NewPassword2' }
it('accepts matching valid passwords', () => expect(() => validatePasswordChange(valid)).not.toThrow())
it('requires the current password', () => expect(() => validatePasswordChange({ ...valid, current_password: '' })).toThrow('current password'))
it.each(['Short1', 'lowercase1', 'UPPERCASE1', 'NoNumbers', `Aa1${'x'.repeat(126)}`])('rejects a new password outside the contract: %s', (password) => expect(() => validatePasswordChange({ ...valid, new_password: password, confirm_password: password })).toThrow('8–128'))
it('requires an exact confirmation', () => expect(() => validatePasswordChange({ ...valid, confirm_password: 'NewPassword2 ' })).toThrow('do not match'))
it('preserves spaces rather than silently changing credentials', () => {
  const value = { current_password: ' OldPassword1 ', new_password: ' NewPassword2 ', confirm_password: ' NewPassword2 ' }
  validatePasswordChange(value)
  expect(value.new_password).toBe(' NewPassword2 ')
  expect(value.current_password).toBe(' OldPassword1 ')
})
