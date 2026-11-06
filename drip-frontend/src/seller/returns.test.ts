import { expect, it } from 'vitest'
import { confirmSellerReturn, sellerReturnActions, sellerReturnBody, validateSellerReturn, validateSellerReturns, type SellerReturnDetail } from './returns'
const id = '11111111-1111-4111-8111-111111111111', orderId = '22222222-2222-4222-8222-222222222222', shipmentId = '33333333-3333-4333-8333-333333333333'
const row: SellerReturnDetail = { id, order_id: orderId, seller_order_id: shipmentId, status: 'requested', reason: 'The item does not fit.', item_count: 1, requested_at: '2026-10-28T10:00:00Z', resolved_at: null, notes: 'Saved notes', order_number: 'WHZ-001', items: [{ id: shipmentId, order_item_id: orderId, product_id: id, variant_id: shipmentId, product_name: 'Linen shirt', variant_label: 'M · Blue', unit_price: '2500.00', purchased_quantity: 2, requested_quantity: 1, line_subtotal: '2500.00', reason: null }], estimated_refund_amount: '2250.00', available_actions: ['approve', 'reject'], refund_status: null, dispute_status: null }
it('validates partial quantities and a discounted refund estimate', () => { expect(validateSellerReturn(row, id)).toEqual(row) })
it('rejects a wrong return ID and invalid quantity or estimate', () => {
  expect(() => validateSellerReturn(row, orderId)).toThrow()
  expect(() => validateSellerReturn({ ...row, estimated_refund_amount: '3000.00' }, id)).toThrow()
  expect(() => validateSellerReturn({ ...row, items: [{ ...row.items[0], requested_quantity: 3 }] }, id)).toThrow()
})
it.each(['received', 'rejected', 'refunded', 'constructor'])('%s cannot gain actions from an unexpected server action', (status) => {
  expect(sellerReturnActions({ ...row, status, available_actions: ['approve', 'reject', 'mark_received', 'request_refund'] })).toEqual([])
})
it('only exposes the intersection of state and server actions', () => {
  expect(sellerReturnActions({ ...row, available_actions: ['reject', 'request_refund'] })).toEqual(['reject'])
  expect(sellerReturnActions({ ...row, status: 'approved', available_actions: ['mark_received'] })).toEqual(['mark_received'])
  expect(sellerReturnActions({ ...row, available_actions: [] })).toEqual([])
})
it('preserves existing notes on blank input and trims explicit replacements', () => {
  expect(sellerReturnBody('approve', '   ', row)).toEqual({})
  expect(sellerReturnBody('reject', '  Outside policy  ', row)).toEqual({ admin_note: 'Outside policy' })
  expect(() => sellerReturnBody('approve', 'x'.repeat(501), row)).toThrow()
  expect(() => sellerReturnBody('mark_received', '', row)).toThrow()
})
it('confirms state and note and rejects wrong order or altered quantities', () => {
  const saved = { ...row, status: 'approved', notes: 'Approved note', available_actions: ['mark_received'] }
  expect(confirmSellerReturn(saved, row, 'approve', { admin_note: 'Approved note' })).toEqual(saved)
  expect(() => confirmSellerReturn({ ...saved, seller_order_id: id }, row, 'approve', {})).toThrow()
  expect(() => confirmSellerReturn(saved, row, 'reject', {})).toThrow()
  expect(() => confirmSellerReturn(saved, row, 'approve', { admin_note: 'Different' })).toThrow()
})
it('uses seller pagination of 25 and validates status filters', () => {
  const page = { data: [row], total: 26, page: 1, total_pages: 2 }
  expect(validateSellerReturns(page, 1, '')).toEqual(page)
  expect(() => validateSellerReturns(page, 2, '')).toThrow()
  expect(() => validateSellerReturns(page, 1, 'received')).toThrow()
  expect(() => validateSellerReturns({ ...page, data: [row, row] }, 1, '')).toThrow()
})
