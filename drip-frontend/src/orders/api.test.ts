import { expect, it } from 'vitest'
import { orderDate, orderPath, statusLabel, validateOrderDetail, validateOrders, type OrderDetail, type OrderList } from './api'

const id = '11111111-1111-4111-8111-111111111111'
const detail: OrderDetail = { id, order_number: 'WHZ-1', status: 'processing', payment_method: 'cod', created_at: '2026-10-21T01:00:00Z', subtotal: '100.10', discount_amount: '5.05', shipping_fee: '20.00', total: '115.05', notes: null, address: null, items: [], seller_orders: [] }
const list: OrderList = { data: [{ id, order_number: 'WHZ-1', status: 'processing', created_at: detail.created_at, total: '115.05', item_count: 2 }], pagination: { page: 1, per_page: 10, total: 1, total_pages: 1 } }
it('uses the exact ID route or a safely encoded order number', () => {
  expect(orderPath(id)).toBe(`/orders/${id}`)
  expect(orderPath(' WHZ-1 ')).toBe('/orders/number/WHZ-1')
  expect(orderPath('a/b?token=secret')).toBe('/orders/number/a%2Fb%3Ftoken%3Dsecret')
  expect(() => orderPath('')).toThrow()
  expect(() => orderPath('x\ny')).toThrow()
})
it('validates server pagination instead of guessing page availability', () => {
  expect(validateOrders(list)).toBe(list)
  expect(() => validateOrders({ ...list, pagination: { ...list.pagination, total_pages: 0 } })).toThrow()
  expect(() => validateOrders({ ...list, data: [{ ...list.data[0], total: 'NaN' }] })).toThrow()
})
it('checks monetary consistency without recomputing prices from the current catalogue', () => {
  expect(validateOrderDetail(detail)).toBe(detail)
  expect(() => validateOrderDetail({ ...detail, total: '115' })).toThrow()
  expect(() => validateOrderDetail({ ...detail, seller_orders: null } as unknown as OrderDetail)).toThrow()
})
it('does not invent progress for unknown order states or invalid dates', () => {
  expect(statusLabel('pending_cod_verification')).toBe('Awaiting COD verification')
  expect(statusLabel('returned')).toBe('Returned')
  expect(statusLabel('unexpected')).toBe('Status unavailable')
  expect(orderDate('invalid')).toBe('Date unavailable')
  expect(orderDate('2026-10-20T23:30:00Z')).toContain('21')
})
