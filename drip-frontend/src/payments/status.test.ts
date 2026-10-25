import { expect, it } from 'vitest'
import { paymentStatusText, validatePaymentStatus, type PaymentStatus } from './status'
const id = '11111111-1111-4111-8111-111111111111'
const value: PaymentStatus = { order_id: id, payment_id: id, status: 'pending', method: 'payfast', amount: '1250.00', gateway_reference: null, paid_at: null }
it('accepts the matching backend payment', () => expect(validatePaymentStatus(value, id)).toBe(value))
it.each([{ order_id: 'foreign' }, { payment_id: 'invalid' }, { amount: '-1' }, { amount: 'NaN' }, { paid_at: 'invalid' }])('rejects malformed or mismatched data %s', (change) => {
  expect(() => validatePaymentStatus({ ...value, ...change }, id)).toThrow()
})
it('keeps unknown statuses neutral', () => {
  expect(paymentStatusText('new-status').label).toBe('Payment status unavailable')
  expect(paymentStatusText('toString').label).toBe('Payment status unavailable')
})
