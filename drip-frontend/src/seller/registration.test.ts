import { expect, it } from 'vitest'
import { extraSlots, samePricing, validateRegistrationPricing, validateRegistrationResult } from './registration'
const pricing = { registration_fee: '5000.00', base_slots: 50, extra_slots: 2, extra_slot_price: '50.00', extra_cost: '100.00', total_cost: '5100.00', total_slots: 52 }

it('validates exact server pricing and zero fees', () => {
  expect(validateRegistrationPricing(pricing, 2)).toEqual(pricing)
  expect(validateRegistrationPricing({ ...pricing, registration_fee: '0', extra_slot_price: '0', extra_cost: '0', total_cost: '0' }, 2).total_cost).toBe('0')
})
it.each(['', '-1', '1.5', '10001', '1e2', 'NaN'])('rejects invalid extra slots %s', (value) => expect(extraSlots(value)).toBeNull())
it.each(['0', '2', '10000'])('accepts bounded extra slots %s', (value) => expect(extraSlots(value)).toBe(Number(value)))
it.each([
  null, { ...pricing, extra_slots: 3 }, { ...pricing, base_slots: -1 }, { ...pricing, total_slots: 51 },
  { ...pricing, extra_cost: '99.00' }, { ...pricing, total_cost: '5000.00' },
  { ...pricing, total_cost: 5100 }, { ...pricing, registration_fee: '-1' }, { ...pricing, extra_slot_price: '0.001' },
])('fails closed on malformed pricing %#', (value) => expect(() => validateRegistrationPricing(value as typeof pricing, 2)).toThrow())
it('compares amounts numerically and catches changes', () => {
  expect(samePricing(pricing, { ...pricing, total_cost: '5100' })).toBe(true)
  expect(samePricing(pricing, { ...pricing, extra_slot_price: '60.00' })).toBe(false)
})
it('accepts a zero-fee receipt without implying approval', () => {
  expect(validateRegistrationResult({ seller_id: '11111111-1111-4111-8111-111111111111', amount_due: '0', message: 'Application submitted' }).amount_due).toBe('0')
})
it.each([null, {}, { seller_id: 'bad', amount_due: '0', message: 'OK' }, { seller_id: '11111111-1111-4111-8111-111111111111', amount_due: '-1', message: 'OK' }])('rejects an unconfirmed response %#', (value) => {
  expect(() => validateRegistrationResult(value as Parameters<typeof validateRegistrationResult>[0])).toThrow()
})
