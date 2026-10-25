export interface Profile { id: string; email: string; first_name: string | null; last_name: string | null; phone: string | null; has_verified_email: boolean }
export interface Address { id: string; label: string | null; street: string; city: string; province: string; is_default: boolean }
export type AddressDraft = Omit<Address, 'id'>
export type ProfileDraft = Record<'first_name' | 'last_name' | 'phone', string>
const uuid = (value: unknown) => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
const optionalText = (value: unknown) => value === null || typeof value === 'string'
export function validateProfile(value: Profile, owner: string): Profile {
  if (!value || value.id !== owner || typeof value.email !== 'string' || typeof value.has_verified_email !== 'boolean' ||
    ![value.first_name, value.last_name, value.phone].every(optionalText)) throw new Error('Profile information could not be verified for this account.')
  return value
}
export function validateAddress(value: Address): Address {
  if (!value || !uuid(value.id) || !optionalText(value.label) || ![value.street, value.city, value.province].every((field) => typeof field === 'string') ||
    typeof value.is_default !== 'boolean') throw new Error('Address information could not be verified.')
  return value
}
export function validateAddresses(value: Address[]): Address[] {
  if (!Array.isArray(value)) throw new Error('The address list could not be verified.')
  value.forEach(validateAddress)
  if (new Set(value.map((item) => item.id)).size !== value.length || value.filter((item) => item.is_default).length > 1) throw new Error('The address list could not be verified.')
  return value
}
export function profileChanges(draft: ProfileDraft, initial: Profile) {
  const changes: Partial<ProfileDraft> = {}
  for (const field of ['first_name', 'last_name', 'phone'] as const) {
    const value = draft[field].trim()
    if (value === (initial[field] ?? '')) continue
    if (!value) throw new Error('The current API cannot clear existing profile values. Restore the value to leave it unchanged.')
    if (field === 'phone' ? !/^(\+92|0092|0)?3[0-9]{9}$/.test(value) : value.length > 100 || !/^[a-zA-Z\s\-'.]+$/.test(value)) {
      throw new Error(field === 'phone' ? 'Enter a valid Pakistani mobile number (03XXXXXXXXX).' : 'Names must be 1–100 characters using letters, spaces, hyphens, apostrophes or periods.')
    }
    changes[field] = value
  }
  return changes
}
export function addressPayload(draft: AddressDraft): AddressDraft {
  const value = { label: (draft.label ?? '').trim(), street: draft.street.trim(), city: draft.city.trim(), province: draft.province.trim(), is_default: draft.is_default }
  if (value.label.length > 50 || value.street.length < 10 || value.street.length > 500 ||
    [value.city, value.province].some((field) => field.length < 2 || field.length > 100)) throw new Error('Use a street address of 10–500 characters, city and province of 2–100 characters, and a label of at most 50 characters.')
  return value
}
