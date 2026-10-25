import { expect, it } from 'vitest'
import { paisa, previewTotal, validateQuote, type CheckoutQuote } from './preview'

const quote = {
  currency: 'PKR', subtotal: '100.10', shipping_fee: '25.25', discount_amount: '0', total: '125.35',
  items: [{ quantity: 1, available_stock: 2 }], payment_methods: [],
  quote_token: 'signed-quote', quote_expires_at: '2030-01-01T00:00:00Z',
} as unknown as CheckoutQuote

it('combines exact server decimal amounts without floating-point rounding', () => {
  expect(previewTotal(quote, { code: 'SAVE', discount_amount: '10.01', new_subtotal: '90.09' })).toBe('115.34')
  expect(previewTotal(quote, null)).toBe('125.35')
  expect(paisa('0.01')).toBe(1n)
})
it.each(['NaN', '-1', '1.001', 'Infinity', '', '1e2'])('rejects invalid currency %s', (value) => {
  expect(() => paisa(value)).toThrow()
})
it('rejects a stale or inconsistent coupon response', () => {
  expect(() => previewTotal(quote, { code: 'OLD', discount_amount: '20', new_subtotal: '90.09' })).toThrow()
  expect(() => previewTotal(quote, { code: 'BAD', discount_amount: '200', new_subtotal: '0' })).toThrow()
})
it('checks quote totals and stock before enabling review', () => {
  expect(validateQuote(quote)).toBe(quote)
  expect(() => validateQuote({ ...quote, total: '1' })).toThrow()
  expect(() => validateQuote({ ...quote, quote_token: '' })).toThrow()
  expect(() => validateQuote({ ...quote, quote_expires_at: 'invalid' })).toThrow()
  expect(() => validateQuote({ ...quote, items: [] })).toThrow()
  expect(() => validateQuote({ ...quote, items: [{ ...quote.items[0], quantity: 3 }] })).toThrow()
})
