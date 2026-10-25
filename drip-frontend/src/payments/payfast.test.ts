import { expect, it } from 'vitest'
import { payfastEndpoint, validateHandoff, type PayFastHandoff } from './payfast'
import type { OrderResult } from '../checkout/submission'
const id = '11111111-1111-4111-8111-111111111111'
const origin = 'https://shop.example.test'
const order: OrderResult = { order_id: id, order_number: 'WHZ-1', status: 'pending_payment', total: '100.00', payment_method: 'payfast', guest_token: null, whatsapp_url: null }
const payload = { MERCHANT_ID: 'fixture', MERCHANT_NAME: 'WearHowZ', TOKEN: 'fixture', PROCCODE: '00', TXNAMT: '100.00', CUSTOMER_MOBILE_NO: '03001234567', CUSTOMER_EMAIL_ADDRESS: 'guest@example.test', SIGNATURE: 'fixture', VERSION: 'WHZ-1.0', TXNDESC: 'Order', SUCCESS_URL: `${origin}/order/success/${id}`, FAILURE_URL: `${origin}/payments/${id}?payment=failed`, BASKET_ID: id, ORDER_DATE: '2026-10-24', CHECKOUT_URL: `${origin}/api/v1/payments/callback/payfast`, CURRENCY_CODE: 'PKR' }
const value: PayFastHandoff = { payment_id: id, attempt_id: id, method: 'payfast', checkout_url: payfastEndpoint, payfast_payload: payload }
it('accepts only a matching order amount, basket and configured endpoints', () => expect(validateHandoff(value, order, origin, origin)).toBe(value))
const changes: Record<string, string>[] = [{ TXNAMT: '101' }, { BASKET_ID: 'other' }, { CURRENCY_CODE: 'USD' }, { TOKEN: '' }, { FAILURE_URL: 'https://evil.test' }, { CHECKOUT_URL: 'https://evil.test' }, { extra: 'unexpected' }]
it.each(changes)('rejects mismatched form %s', (change) => {
  expect(() => validateHandoff({ ...value, payfast_payload: { ...payload, ...change } }, order, origin, origin)).toThrow()
})
it.each(['https://evil.test', `${payfastEndpoint}?redirect=evil`, payfastEndpoint.replace('https:', 'http:'), payfastEndpoint.replace('ipguat', 'ipg1')])('rejects unexpected destination %s', (checkout_url) => {
  expect(() => validateHandoff({ ...value, checkout_url }, order, origin, origin)).toThrow()
})
it('rejects an expired handoff', () => expect(() => validateHandoff({ ...value, expires_at: '2020-01-01' }, order, origin, origin)).toThrow())
it('accepts a provider basket bound to a distinct attempt rather than the order', () => {
  const attempt = '22222222-2222-4222-8222-222222222222'
  const result = { ...value, attempt_id: attempt, payfast_payload: { ...payload, BASKET_ID: attempt } }
  expect(validateHandoff(result, order, origin, origin)).toBe(result)
})
it('rejects handoffs without a valid attempt identity', () => {
  expect(() => validateHandoff({ ...value, attempt_id: '' }, order, origin, origin)).toThrow()
})
