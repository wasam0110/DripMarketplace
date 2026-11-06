import { expect, it } from 'vitest'
import { confirmSettings, sameSettings, settingsDraft, settingsMarker, settingsPayload, validateSettings, type PlatformSettings } from './settings'
const settings = (): PlatformSettings => ({ commission_rate: 0.15, registration_fee: 5000, extra_slot_price: 50, free_shipping_threshold: 5000, standard_shipping_fee: 200, cod_timeout_minutes: 30, wallet_hold_days: 3 })
it('accepts validated effective settings and ignores unrelated response fields', () => {
  expect(validateSettings(settings())).toEqual(settings())
  expect(sameSettings(settings(), { ...settings(), wallet_hold_days: 0 })).toBe(false)
  for (const patch of [{ commission_rate: Infinity }, { registration_fee: '5000' }, { extra_slot_price: 0.5 }, { wallet_hold_days: 31 }, { cod_timeout_minutes: 4 }, { standard_shipping_fee: -1 }, { free_shipping_threshold: Number.MAX_SAFE_INTEGER + 1 }]) expect(() => validateSettings({ ...settings(), ...patch } as PlatformSettings)).toThrow()
})
it('sends only changed fields with the complete review snapshot and supports zeros', () => {
  const before = settings(), draft = { ...settingsDraft(before), registration_fee: '0', wallet_hold_days: '0', commission_rate: '0.125' }
  expect(settingsPayload(before, draft, true)).toEqual({ registration_fee: 0, wallet_hold_days: 0, commission_rate: 0.125, expected_settings: before })
  expect(() => settingsPayload(before, draft, false)).toThrow()
  expect(() => settingsPayload(before, settingsDraft(before), true)).toThrow()
})
it('rejects blanks, exponent notation, fractions for integer fields and out-of-range values', () => {
  const before = settings()
  for (const n of ['', '1e3', '-1', '1.2', 'NaN', '9007199254740992']) expect(() => settingsPayload(before, { ...settingsDraft(before), registration_fee: n }, true)).toThrow()
  for (const n of ['-0.1', '1.01', 'NaN', '']) expect(() => settingsPayload(before, { ...settingsDraft(before), commission_rate: n }, true)).toThrow()
  expect(() => settingsPayload(before, { ...settingsDraft(before), cod_timeout_minutes: '1441' }, true)).toThrow()
})
it('checks both changed and unchanged fields in the saved receipt', () => {
  const before = settings(), body = settingsPayload(before, { ...settingsDraft(before), registration_fee: '0' }, true)
  expect(confirmSettings({ ...before, registration_fee: 0 }, body).registration_fee).toBe(0)
  expect(() => confirmSettings(before, body)).toThrow()
  expect(() => confirmSettings({ ...before, registration_fee: 0, wallet_hold_days: 4 }, body)).toThrow()
  expect(settingsMarker('admin-one')).not.toBe(settingsMarker('admin-two'))
})
