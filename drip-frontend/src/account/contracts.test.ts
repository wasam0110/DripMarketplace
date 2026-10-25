import { describe, expect, it } from 'vitest'
import { addressPayload, profileChanges, validateAddresses, validateProfile } from './contracts'
const profile = { id: 'owner', email: 'test@example.test', first_name: 'Sara', last_name: null, phone: null, has_verified_email: true }
const address = { id: '11111111-1111-4111-8111-111111111111', label: 'Home', street: '123 Example Road', city: 'Karachi', province: 'Sindh', is_default: true }
describe('account contracts', () => {
  it('rejects foreign profile data', () => expect(() => validateProfile(profile, 'someone-else')).toThrow())
  it('checks profile field shapes', () => expect(() => validateProfile({ ...profile, phone: undefined } as never, 'owner')).toThrow())
  it('sends only changed trimmed profile fields', () => expect(profileChanges({ first_name: ' Ayesha ', last_name: '', phone: '' }, profile)).toEqual({ first_name: 'Ayesha' }))
  it('omits unchanged absent fields', () => expect(profileChanges({ first_name: 'Sara', last_name: '', phone: '' }, profile)).toEqual({}))
  it('does not pretend to clear existing values', () => expect(() => profileChanges({ first_name: '', last_name: '', phone: '' }, profile)).toThrow('cannot clear'))
  it('rejects unsupported name characters', () => expect(() => profileChanges({ first_name: 'Sara1', last_name: '', phone: '' }, profile)).toThrow('Names'))
  it('accepts Pakistani phone formats', () => expect(profileChanges({ first_name: 'Sara', last_name: '', phone: '+923001234567' }, profile)).toEqual({ phone: '+923001234567' }))
  it('rejects invalid phones', () => expect(() => profileChanges({ first_name: 'Sara', last_name: '', phone: '123' }, profile)).toThrow('mobile'))
  it('never sends server identifiers in address drafts', () => expect(addressPayload(address)).toEqual({ label: 'Home', street: '123 Example Road', city: 'Karachi', province: 'Sindh', is_default: true }))
  it('clears labels using an empty string', () => expect(addressPayload({ ...address, label: null }).label).toBe(''))
  it('rejects trimmed short addresses', () => expect(() => addressPayload({ ...address, street: '  short  ' })).toThrow())
  it('rejects short locations', () => expect(() => addressPayload({ ...address, city: ' K ' })).toThrow())
  it('rejects duplicate IDs and multiple defaults', () => {
    expect(() => validateAddresses([address, address])).toThrow()
    expect(() => validateAddresses([address, { ...address, id: '22222222-2222-4222-8222-222222222222' }])).toThrow()
  })
})
