import { expect, it } from 'vitest'
import { codMarker, codPayload, confirmCODOrder, confirmCODReceipt, matchCODOrder, sameCODReview, validateCODQueue } from './cod'
import type { AdminOrderDetail } from './orders'
const id = '11111111-1111-4111-8111-111111111111', seller = '22222222-2222-4222-8222-222222222222'
const row = { order_id: id, order_number: 'WHZ-COD', customer_name: 'Snapshot Recipient', customer_phone: '03001234567', total: '1200.25', brand_names: ['Fixture Brand'], placed_at: '2099-01-01T00:00:00Z', expires_at: '2099-01-01T00:30:00Z', minutes_remaining: 29, updated_at: '2099-01-01T00:00:00Z' }
const order: AdminOrderDetail = { id, order_number: row.order_number, status: 'pending_cod_verification', payment_method: 'cod', customer_name: row.customer_name, user_id: null, commission: '0', subtotal: '1000.25', discount_amount: '0', shipping_fee: '200', total: row.total, notes: null, created_at: row.placed_at, address: { recipient_name: row.customer_name, phone: row.customer_phone, street: 'Test street', city: 'Lahore', province: 'Punjab', note: null }, items: [{ id, seller_id: seller, product_id: id, variant_id: id, product_name: 'Saved shirt', variant_label: 'M', quantity: 1, unit_price: '1000.25', subtotal: '1000.25' }], seller_orders: [{ id, seller_id: seller, brand_name: 'Fixture Brand', status: 'pending', subtotal: '1000.25', tracking_number: null, courier_name: null, shipped_at: null, delivered_at: null }] }
it('validates unique queue identities, explicit versions and bounded timestamps', () => {
  expect(validateCODQueue([row])).toEqual([row]); expect(validateCODQueue([])).toEqual([])
  for (const changes of [{ updated_at: undefined }, { order_id: 'invalid' }, { total: 'NaN' }, { minutes_remaining: -1 }, { expires_at: row.placed_at }]) expect(() => validateCODQueue([{ ...row, ...changes } as typeof row])).toThrow()
  expect(() => validateCODQueue([row, row])).toThrow()
})
it('matches only the pending COD order and its displayed customer/brand/amount snapshot', () => {
  expect(matchCODOrder(row, order)).toBe(order)
  for (const changes of [{ id: seller }, { status: 'processing' }, { payment_method: 'payfast' }, { total: '999.99' }, { address: { ...order.address!, phone: 'changed' } }, { seller_orders: [] }]) expect(() => matchCODOrder(row, { ...order, ...changes })).toThrow()
})
it('binds confirmed decisions to both reviewed order and runtime deadline versions', () => {
  expect(codPayload('verify', ' Checked ', true, row, Date.parse(row.placed_at))).toEqual({ note: 'Checked', expected_updated_at: row.updated_at, expected_expires_at: row.expires_at })
  expect(() => codPayload('verify', '', false, row)).toThrow()
  expect(() => codPayload('verify', '', true, row, Date.parse(row.expires_at))).toThrow()
  expect(() => codPayload('verify', '', true, { ...row, customer_phone: '' }, Date.parse(row.placed_at))).toThrow()
})
it('allows reviewed cancellation after expiry but requires a clear reason', () => {
  expect(codPayload('cancel', 'Customer did not respond', true, row, Date.parse(row.expires_at)).note).toBe('Customer did not respond')
  expect(() => codPayload('cancel', 'short', true, row)).toThrow()
  expect(() => codPayload('verify', 'line\nbreak', true, row)).toThrow()
  expect(() => codPayload('verify', 'x'.repeat(501), true, row)).toThrow()
})
it('ignores only volatile minutes remaining during final preflight', () => {
  expect(sameCODReview(row, order, { ...row, minutes_remaining: 10 }, order)).toBe(true)
  for (const changes of [{ updated_at: '2099-01-01T00:01:00Z' }, { expires_at: '2099-01-01T00:40:00Z' }, { customer_phone: 'changed' }]) expect(sameCODReview(row, order, { ...row, ...changes }, order)).toBe(false)
  expect(sameCODReview(row, order, row, { ...order, notes: 'Changed note' })).toBe(false)
})
it('verifies structured receipts and private readback without calling approval a payment', () => {
  expect(confirmCODReceipt({ order_id: id, order_number: row.order_number, status: 'processing', message: 'Approved' }, row, 'verify').status).toBe('processing')
  expect(() => confirmCODReceipt({ order_id: seller, order_number: row.order_number, status: 'processing', message: 'Approved' }, row, 'verify')).toThrow()
  expect(confirmCODOrder({ ...order, status: 'processing' }, row, 'verify').payment_method).toBe('cod')
  expect(() => confirmCODOrder({ ...order, status: 'processing', items: [] }, row, 'verify', order)).toThrow()
  expect(() => confirmCODOrder({ ...order, status: 'cancelled' }, row, 'cancel')).toThrow()
  expect(confirmCODOrder({ ...order, status: 'cancelled', seller_orders: [{ ...order.seller_orders[0], status: 'cancelled' }] }, row, 'cancel').status).toBe('cancelled')
})
it('isolates ambiguous-action markers by owner and order', () => { expect(codMarker('a', id)).not.toBe(codMarker('b', id)); expect(codMarker('a', id)).not.toBe(codMarker('a', seller)) })
