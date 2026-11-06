import { expect, it } from 'vitest'
import { completeShippingAddress, confirmFulfilment, fulfilmentChange, nextFulfilment, validateFulfilmentDetail, validateFulfilmentPage, type FulfilmentDetail } from './fulfilment'
const order: FulfilmentDetail = { id: '33333333-3333-4333-8333-333333333333', order_id: '22222222-2222-4222-8222-222222222222', order_number: 'WHZ-001', status: 'pending', subtotal: '5000.00', tracking_number: null, courier_name: null, shipped_at: null, delivered_at: null, created_at: '2026-10-28T10:00:00+00:00',
  shipping_address: { recipient_name: 'Customer', phone: '03001234567', street: 'Test street', city: 'Lahore', province: 'Punjab', note: null }, items: [{ product_name: 'Linen shirt', variant_label: 'M · Blue', unit_price: '2500.00', quantity: 2, subtotal: '5000.00' }] }
it.each([['pending', 'processing'], ['processing', 'shipped'], ['shipped', 'delivered'], ['delivered', null], ['cancelled', null], ['constructor', null]])('only offers the next step for %s', (status, target) => {
  expect(nextFulfilment(status)).toBe(target)
})
it('sends tracking only with shipment and trims bounded text', () => {
  expect(fulfilmentChange(order, 'ignored', 'ignored')).toEqual({ status: 'processing' })
  expect(fulfilmentChange({ ...order, status: 'processing' }, ' PK123 ', ' Courier ')).toEqual({ status: 'shipped', tracking_number: 'PK123', courier_name: 'Courier' })
  expect(() => fulfilmentChange({ ...order, status: 'processing' }, '  ', '')).toThrow()
  expect(() => fulfilmentChange({ ...order, status: 'processing' }, 'X'.repeat(101), '')).toThrow()
})
it('requires seller-order identity and item arithmetic', () => {
  expect(validateFulfilmentDetail(order, order.id)).toEqual(order)
  expect(() => validateFulfilmentDetail(order, order.order_id)).toThrow()
  expect(() => validateFulfilmentDetail({ ...order, subtotal: '4000' }, order.id)).toThrow()
  expect(() => validateFulfilmentDetail({ ...order, items: [{ ...order.items[0], quantity: 3 }] }, order.id)).toThrow()
})
it('checks the returned state, parent ID and submitted tracking', () => {
  const before = { ...order, status: 'processing' }, change = fulfilmentChange(before, 'PK123', 'Courier')
  const saved = { ...before, status: 'shipped', tracking_number: 'PK123', courier_name: 'Courier' }
  expect(confirmFulfilment(saved, before, change)).toEqual(saved)
  expect(() => confirmFulfilment({ ...saved, order_id: order.id }, before, change)).toThrow()
  expect(() => confirmFulfilment({ ...saved, tracking_number: 'WRONG' }, before, change)).toThrow()
  expect(() => confirmFulfilment(before, before, change)).toThrow()
})
it('validates filtered pages and rejects duplicate shipments', () => {
  const page = { data: [order], pagination: { page: 1, per_page: 25, total: 1, total_pages: 1 } }
  expect(validateFulfilmentPage(page, 1, 'pending')).toEqual(page)
  expect(() => validateFulfilmentPage(page, 1, 'shipped')).toThrow()
  expect(() => validateFulfilmentPage({ ...page, data: [order, order] }, 1, 'all')).toThrow()
})
it('identifies missing delivery fields without inventing address data', () => {
  expect(completeShippingAddress(order.shipping_address)).toBe(true)
  expect(completeShippingAddress({ ...order.shipping_address, street: '' })).toBe(false)
})
