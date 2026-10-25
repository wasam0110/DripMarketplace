import { describe, expect, it } from 'vitest'
import { changedPreferences, preferenceKeys, validatePreferences } from './preferences'
const initial = { email_order_updates: true, email_promotions: false, email_new_arrivals: false, sms_order_updates: false, whatsapp_order_updates: true }
describe('notification preference contracts', () => {
  it('preserves true and false values without inventing defaults', () => expect(validatePreferences(initial)).toEqual(initial))
  it.each(preferenceKeys)('requires a boolean for %s', (key) => {
    expect(() => validatePreferences({ ...initial, [key]: undefined })).toThrow()
    expect(() => validatePreferences({ ...initial, [key]: 'false' })).toThrow()
  })
  it('sends only explicitly changed keys, including false', () => expect(changedPreferences(initial, { ...initial, email_order_updates: false, email_new_arrivals: true })).toEqual({ email_order_updates: false, email_new_arrivals: true }))
  it('omits unchanged settings', () => expect(changedPreferences(initial, initial)).toEqual({}))
  it('does not propagate unrelated settings', () => expect(validatePreferences({ ...initial, payout_notifications: true } as typeof initial)).toEqual(initial))
})
