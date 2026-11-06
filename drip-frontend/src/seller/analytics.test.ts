import { expect, it } from 'vitest'
import { analyticsMoney, validateCommission, validateCommissionEntry, validateInventoryHealth, validateOverview, validateRevenue, validateTopProducts, type CommissionEntry, type CommissionSummary } from './analytics'
const id = '11111111-1111-4111-8111-111111111111'
const entry: CommissionEntry = { id, seller_order_id: id, commission_rate: 0.15, settled_at: '2026-10-28T10:00:00Z', released_at: null,
  gross_amount: '1000.20', commission_amount: '150.03', seller_amount: '850.17', original_gross_amount: '1500.25', original_commission_amount: '225.04', original_seller_amount: '1275.21',
  refunded_gross_amount: '500.05', reversed_commission_amount: '75.01', reversed_seller_amount: '425.04', recovered_seller_amount: '400', settlement_offset_amount: '25.04', platform_shortfall_amount: '0' }
const summary: CommissionSummary = { total_gross: '1000.20', total_commission: '150.03', total_net: '850.17', original_gross: '1500.25', original_commission: '225.04', original_net: '1275.21',
  total_refunded_gross: '500.05', total_reversed_commission: '75.01', total_reversed_seller: '425.04', total_recovered_seller: '400', total_settlement_offset: '25.04', total_platform_shortfall: '0' }
const overview = { period: '30d', gross_revenue: '1000.20', commission_paid: '150.03', net_earnings: '850.17', order_count: 1, units_sold: 2, avg_order_value: '1000.20', total_views: 10, conversion_rate: 10 }
it('preserves aggregate precision past Number safe integer limits', () => {
  expect(analyticsMoney('9007199254740993.25')).toBe('PKR 9,007,199,254,740,993.25')
  expect(analyticsMoney('0001.2')).toBe('PKR 1.20')
})
it.each(['1e3', 'Infinity', '-1', '1.005', '', 'NaN'])('rejects malformed money %s', (value) => expect(() => analyticsMoney(value)).toThrow())
it('accepts balanced overview without imposing a misleading 100% ratio cap', () => {
  expect(validateOverview({ ...overview, conversion_rate: 200 }, '30d').conversion_rate).toBe(200)
  expect(() => validateOverview(overview, '7d')).toThrow()
  expect(() => validateOverview({ ...overview, net_earnings: '850.18' }, '30d')).toThrow()
  expect(() => validateOverview({ ...overview, total_views: 0.5 }, '30d')).toThrow()
  expect(() => validateOverview({ ...overview, conversion_rate: NaN }, '30d')).toThrow()
})
it('validates ordered UTC revenue buckets and requested dimensions', () => {
  const series = { period: '30d', granularity: 'week', data: [{ date: '2026-10-26', gross: '1000.20', commission: '150.03', net: '850.17', orders: 1 }] }
  expect(validateRevenue(series, '30d', 'week')).toBe(series)
  expect(() => validateRevenue(series, '30d', 'day')).toThrow()
  expect(() => validateRevenue({ ...series, data: [...series.data, ...series.data] }, '30d', 'week')).toThrow()
  expect(() => validateRevenue({ ...series, data: [{ ...series.data[0], date: '2026-02-30' }] }, '30d', 'week')).toThrow()
})
it('validates product identifiers, rating, count and ranking response', () => {
  const products = { period: '30d', sort_by: 'views', data: [{ product_id: id, product_name: 'Coat', revenue: '1000.20', units_sold: 1, views: 100, avg_rating: 4.5 }] }
  expect(validateTopProducts(products, '30d', 'views')).toBe(products)
  expect(() => validateTopProducts(products, '30d', 'units')).toThrow()
  expect(() => validateTopProducts({ ...products, data: [...products.data, ...products.data] }, '30d', 'views')).toThrow()
  expect(() => validateTopProducts({ ...products, data: [{ ...products.data[0], avg_rating: 6 }] }, '30d', 'views')).toThrow()
})
it('counts low stock within in-stock variants, not as a separate additive total', () => {
  const stock = { total_variants: 5, in_stock: 3, low_stock: 2, out_of_stock: 2, total_units: 8 }
  expect(validateInventoryHealth(stock)).toBe(stock)
  expect(() => validateInventoryHealth({ ...stock, low_stock: 4 })).toThrow()
  expect(() => validateInventoryHealth({ ...stock, out_of_stock: 3 })).toThrow()
})
it('accepts exact partial refunds and preserves distinct recovery channels', () => {
  expect(validateCommissionEntry(entry)).toBe(entry)
  expect(() => validateCommissionEntry({ ...entry, seller_amount: '850.16' })).toThrow()
  expect(() => validateCommissionEntry({ ...entry, released_at: 'not a date' })).toThrow()
  expect(() => validateCommissionEntry({ ...entry, commission_rate: 15 })).toThrow()
})
it('accepts a full refund without inferring a bank payout from release', () => {
  expect(validateCommissionEntry({ ...entry, gross_amount: '0', commission_amount: '0', seller_amount: '0', refunded_gross_amount: '1500.25', reversed_commission_amount: '225.04', reversed_seller_amount: '1275.21', released_at: '2026-10-28T12:00:00Z' }).seller_amount).toBe('0')
})
it('requires all summary refund fields and checks exact original/net reconciliation', () => {
  const page = { data: [entry], summary, total: 26, page: 1 }
  expect(validateCommission(page, 1)).toBe(page)
  expect(() => validateCommission({ ...page, summary: { ...summary, total_reversed_seller: '425.03' } }, 1)).toThrow()
  expect(() => validateCommission({ ...page, summary: { ...summary, total_platform_shortfall: undefined! } }, 1)).toThrow()
  expect(() => validateCommission(page, 2)).toThrow()
  expect(() => validateCommission({ ...page, data: [entry, entry] }, 1)).toThrow()
})
