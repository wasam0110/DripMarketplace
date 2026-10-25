import { expect, it } from 'vitest'
import { confirmReturn, returnPayload } from './returns'
import type { OrderDetail } from './api'

const id = '11111111-1111-4111-8111-111111111111'
const second = '22222222-2222-4222-8222-222222222222'
const order = { id, status: 'delivered', items: [{ id, seller_id: 'brand', quantity: 2 }, { id: second, seller_id: 'other', quantity: 1 }], seller_orders: [{ id, seller_id: 'brand' }, { id: second, seller_id: 'other' }] } as OrderDetail
it('builds one-brand requests with trimmed reasons and purchased quantities', () => {
  expect(returnPayload(order, { [id]: 2 }, '  Not the expected fit  ')).toEqual({ seller_order_id: id, reason: 'Not the expected fit', items: [{ order_item_id: id, quantity: 2 }] })
})
it('rejects mixed brands, invalid items, quantity bounds and short reasons', () => {
  const invalid: Record<string, number>[] = [{}, { [id]: 0 }, { [id]: 3 }, { [id]: 1.5 }, { missing: 1 }, { [id]: 1, [second]: 1 }]
  for (const quantities of invalid) {
    expect(() => returnPayload(order, quantities, 'Not the expected fit')).toThrow()
  }
  for (const reason of ['short', ' '.repeat(20), 'x'.repeat(1001)]) expect(() => returnPayload(order, { [id]: 1 }, reason)).toThrow()
})
it('rejects undelivered orders and unresolved shipment mapping', () => {
  expect(() => returnPayload({ ...order, status: 'processing' }, { [id]: 1 }, 'Not the expected fit')).toThrow(/delivered/)
  expect(() => returnPayload({ ...order, seller_orders: [] }, { [id]: 1 }, 'Not the expected fit')).toThrow(/shipment/)
})
it('confirms only a matching requested return', () => {
  const payload = returnPayload(order, { [id]: 1 }, 'Not the expected fit')
  const receipt = { ...payload, id: second, order_id: id, status: 'requested' }
  expect(confirmReturn(receipt, id, payload)).toBe(receipt)
  for (const change of [{ order_id: second }, { seller_order_id: second }, { status: 'approved' }, { reason: 'Different reason' }, { items: [] }, { items: [...payload.items, ...payload.items] }, { items: [{ order_item_id: id, quantity: 2 }] }]) {
    expect(() => confirmReturn({ ...receipt, ...change }, id, payload)).toThrow(/could not be confirmed/)
  }
})
