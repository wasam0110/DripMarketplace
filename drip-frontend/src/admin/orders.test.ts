import { expect, it } from 'vitest'
import { adminOrderQuery, adminOrderWarnings, paymentMethodLabel, validateAdminOrderDetail, validateAdminOrders, type AdminOrderDetail } from './orders'
import { sellerMoney } from './sellers'
const id = '11111111-1111-4111-8111-111111111111', seller = '22222222-2222-4222-8222-222222222222', other = '33333333-3333-4333-8333-333333333333'
const row = { id, order_number: 'WHZ-TEST', status: 'processing', customer_name: 'Snapshot Recipient', seller_count: 1, subtotal: '1000.25', total: '1100.45', commission: '80.03', payment_method: 'cod', created_at: '2026-10-28T00:00:00Z' }
const detail: AdminOrderDetail = { ...row, user_id: null, discount_amount: '100.05', shipping_fee: '200.25', notes: null, address: { recipient_name: 'Snapshot Recipient', phone: '03001234567', street: 'Test street', city: 'Lahore', province: 'Punjab', note: null }, items: [{ id: other, seller_id: seller, product_id: other, variant_id: other, product_name: 'Saved item', variant_label: 'M / Ivory', unit_price: '1000.25', quantity: 1, subtotal: '1000.25' }], seller_orders: [{ id: other, seller_id: seller, brand_name: 'Brand', status: 'shipped', subtotal: '1000.25', tracking_number: 'TRACK', courier_name: null, shipped_at: '2026-10-28T00:00:00Z', delivered_at: null }] }
it('sends only supported status, payment, seller and pagination parameters', () => {
  expect(adminOrderQuery('all', 'all', '', '1')).toBe('page=1&per_page=25')
  expect(adminOrderQuery('processing', 'cod', ` ${seller} `, '2')).toBe(`page=2&per_page=25&status=processing&payment_method=cod&seller_id=${seller}`)
  for (const args of [['pending', 'all', '', '1'], ['all', 'card', '', '1'], ['all', 'all', 'bad', '1'], ['all', 'all', '', '0'], ['all', 'all', '', '999999999999999999']]) expect(() => adminOrderQuery(...args as [string, string, string, string])).toThrow()
})
it('validates the applied page, filtered rows, unique IDs and all-matching totals', () => {
  const page = { data: [row], totals: { total_gmv: '3302.30', total_commission: '150.06', order_count: 26 }, total: 26, page: 1, per_page: 25, total_pages: 2 }
  expect(validateAdminOrders(page, 1, 'all', 'all')).toBe(page)
  for (const bad of [{ ...page, data: [row, row] }, { ...page, totals: { ...page.totals, order_count: 1 } }, { ...page, total_pages: 1 }, { ...page, per_page: 100 }]) expect(() => validateAdminOrders(bad, 1, 'all', 'all')).toThrow()
  expect(() => validateAdminOrders(page, 1, 'shipped', 'all')).toThrow(); expect(() => validateAdminOrders(page, 1, 'all', 'payfast')).toThrow()
})
it('preserves exact aggregate amounts beyond floating point precision', () => { expect(sellerMoney('9007199254740993.25')).toBe('PKR 9,007,199,254,740,993.25') })
it('requires the requested detail identity, complete types and unique item/shipment references', () => {
  expect(validateAdminOrderDetail(detail, id)).toBe(detail)
  for (const changes of [{ id: other }, { commission: undefined }, { address: undefined }, { items: [detail.items[0], detail.items[0]] }, { seller_orders: [detail.seller_orders[0], detail.seller_orders[0]] }, { user_id: 'bad' }]) expect(() => validateAdminOrderDetail({ ...detail, ...changes } as AdminOrderDetail, id)).toThrow()
})
it('does not rewrite inconsistent historical checkout amounts while flagging them', () => {
  expect(adminOrderWarnings(detail)).toEqual([])
  const corrupt = { ...detail, total: '999.99', items: [{ ...detail.items[0], quantity: 2 }], seller_orders: [{ ...detail.seller_orders[0], subtotal: '800.00' }] }
  expect(validateAdminOrderDetail(corrupt, id).total).toBe('999.99'); expect(adminOrderWarnings(corrupt)).toHaveLength(3)
})
it('allows explicit missing address/items/splits with operational warnings rather than fabricating data', () => {
  const partial = { ...detail, address: null, items: [], seller_orders: [] }
  expect(validateAdminOrderDetail(partial, id)).toBe(partial); expect(adminOrderWarnings(partial)).toHaveLength(3)
})
it('reads historical payment methods without offering them in new payment filters', () => {
  expect(validateAdminOrderDetail({ ...detail, payment_method: 'card' }, id).payment_method).toBe('card'); expect(paymentMethodLabel('card')).toBe('Card (historical)'); expect(paymentMethodLabel('future')).toBe('Method unavailable')
})
