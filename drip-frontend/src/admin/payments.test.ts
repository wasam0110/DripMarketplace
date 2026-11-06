import { expect, it } from 'vitest'
import { collectionMarker, collectionPayload, confirmCollection, confirmCollectionReadback, paymentQuery, paymentStatusLabel, samePaymentReview, validatePayment, validatePayments, type AdminPayment } from './payments'
const id = '11111111-1111-4111-8111-111111111111', owner = '22222222-2222-4222-8222-222222222222'
const payment = (): AdminPayment => ({ id, order_id: owner, order_number: 'WHZ-001', method: 'cod', status: 'pending', amount: '1200.25', gateway_reference: null, paid_at: null, created_at: '2026-11-01T00:00:00Z', currency: 'PKR', order_status: 'delivered', order_updated_at: '2026-11-01T01:00:00Z', can_record_cod_collection: true, collection_blockers: [], collection_recorded_by: null })
it('uses payment states rather than misleading fulfilment labels', () => {
  expect(['pending', 'processing', 'completed', 'failed', 'refunded', 'unknown'].map(paymentStatusLabel)).toEqual(['Awaiting payment / collection', 'Payment processing', 'Completed', 'Failed', 'Refunded', 'Status unavailable'])
})
it('validates exact decimal payments and filter-aware pagination', () => {
  const value = { data: [payment()], total: 1, page: 1, per_page: 25, total_pages: 1 }
  expect(validatePayments(value, 1, 'pending', 'cod')).toBe(value)
  for (const bad of [{ ...value, page: 2 }, { ...value, total_pages: 2 }, { ...value, data: [payment(), payment()] }, { ...value, data: [{ ...payment(), amount: 1200.25 }] }]) expect(() => validatePayments(bad as typeof value, 1, 'pending', 'cod')).toThrow()
  expect(() => validatePayments(value, 1, 'completed', 'cod')).toThrow()
})
it('validates URL filters without inventing historical checkout methods', () => {
  expect(paymentQuery('all', 'all', '2')).toBe('page=2')
  expect(paymentQuery('pending', 'cod', '1')).toBe('page=1&status=pending&method=cod')
  for (const args of [['bad', 'cod', '1'], ['all', 'card', '1'], ['all', 'all', '0'], ['all', 'all', '1e3']]) expect(() => paymentQuery(...args as [string, string, string])).toThrow()
})
it('rejects wrong identity, missing eligibility and inconsistent collection capability', () => {
  expect(validatePayment(payment(), id).id).toBe(id)
  for (const fields of [{ id: owner }, { can_record_cod_collection: undefined }, { currency: 'USD' }, { order_status: 'shipped' }, { collection_blockers: ['Not delivered'] }, { paid_at: '2026-11-01T01:00:00Z' }]) expect(() => validatePayment({ ...payment(), ...fields } as AdminPayment, id)).toThrow()
  expect(validatePayment({ ...payment(), method: 'card', can_record_cod_collection: false, collection_blockers: ['Historical method'] }, id).method).toBe('card')
})
it('requires receipt confirmation and submits the exact saved amount and order version', () => {
  expect(collectionPayload(payment(), '  RECEIPT-001  ', true)).toEqual({ reference: 'RECEIPT-001', expected_amount: '1200.25', expected_order_updated_at: payment().order_updated_at })
  for (const reference of ['', 'ab', 'a\nb', 'x'.repeat(256)]) expect(() => collectionPayload(payment(), reference, true)).toThrow()
  expect(() => collectionPayload(payment(), 'REC-001', false)).toThrow()
})
it('rejects changed preflight evidence and isolates pending markers by owner and payment', () => {
  expect(samePaymentReview(payment(), payment())).toBe(true)
  expect(samePaymentReview(payment(), { ...payment(), order_updated_at: '2026-11-01T02:00:00Z' })).toBe(false)
  expect(collectionMarker(owner, id)).not.toBe(collectionMarker(id, id))
  expect(collectionMarker(owner, id)).not.toBe(collectionMarker(owner, owner))
})
it('requires a structured receipt matching amount, order, reference and acting administrator', () => {
  const receipt = { payment_id: id, order_id: owner, order_number: 'WHZ-001', status: 'completed', amount: '1200.25', currency: 'PKR', reference: 'REC-001', paid_at: '2026-11-01T02:00:00Z', recorded_by: owner }
  expect(confirmCollection(receipt, payment(), 'REC-001', owner)).toBe(receipt)
  for (const fields of [{ payment_id: owner }, { order_id: id }, { amount: '1200.24' }, { recorded_by: id }, { reference: 'OTHER' }, { paid_at: null }]) expect(() => confirmCollection({ ...receipt, ...fields } as typeof receipt, payment(), 'REC-001', owner)).toThrow()
  const saved = { ...payment(), status: 'completed', gateway_reference: receipt.reference, paid_at: receipt.paid_at, collection_recorded_by: owner, can_record_cod_collection: false, collection_blockers: ['Payment is not awaiting collection.'] }
  expect(confirmCollectionReadback(saved, payment(), receipt)).toBe(saved)
  expect(() => confirmCollectionReadback({ ...saved, gateway_reference: 'OTHER' }, payment(), receipt)).toThrow()
  expect(() => confirmCollectionReadback({ ...saved, collection_recorded_by: null }, payment(), receipt)).toThrow()
})
