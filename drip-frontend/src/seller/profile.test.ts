import { expect, it } from 'vitest'
import { brandChanges, brandDraft, confirmBrandUpdate, validateBrandProfile } from './profile'
const profile = { id: '11111111-1111-4111-8111-111111111111', brand_name: 'Fixture Label', description: 'Our label', return_policy: null, whatsapp_number: '03001234567', instagram_handle: null, brand_color: '#203C32' }
it('validates only displayed fields and drops unexpected properties', () => {
  expect(validateBrandProfile({ ...profile, status: 'active' } as typeof profile)).toEqual(profile)
})
it('does not write unchanged nullable fields', () => expect(brandChanges(brandDraft(profile), profile)).toEqual({}))
it('sends only changed whitelisted fields, including explicit clearing', () => {
  expect(brandChanges({ ...brandDraft(profile), description: '', instagram_handle: 'our_label', status: 'active', brand_name: 'Changed' } as ReturnType<typeof brandDraft>, profile)).toEqual({ description: '', instagram_handle: 'our_label' })
})
it.each([
  null, {}, { ...profile, id: 'bad' }, { ...profile, brand_name: '' },
  { ...profile, description: 123 }, { ...profile, return_policy: undefined },
  { ...profile, whatsapp_number: '0'.repeat(21) }, { ...profile, instagram_handle: 'a'.repeat(101) },
  { ...profile, description: 'a'.repeat(2001) }, { ...profile, brand_color: 'red' },
])('rejects malformed profile %#', (value) => expect(() => validateBrandProfile(value as typeof profile)).toThrow())
it.each([
  { brand_color: '#fff' }, { brand_color: '' }, { description: 'a'.repeat(2001) },
  { return_policy: 'a'.repeat(1001) }, { whatsapp_number: 'a'.repeat(21) }, { instagram_handle: 'a'.repeat(101) },
])('validates update limits %#', (changes) => expect(() => brandChanges({ ...brandDraft(profile), ...changes }, profile)).toThrow())
it('confirms identity and the exact requested values', () => {
  expect(confirmBrandUpdate({ ...profile, description: 'Updated' }, profile, { description: 'Updated' }).description).toBe('Updated')
  expect(() => confirmBrandUpdate(profile, profile, { description: 'Updated' })).toThrow()
  expect(() => confirmBrandUpdate({ ...profile, id: '22222222-2222-4222-8222-222222222222' }, profile, {})).toThrow()
})
