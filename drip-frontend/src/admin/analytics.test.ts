import { expect, it } from 'vitest'
import { analyticsMoney, validatePlatform, validateRevenue, validateTopSellers } from './analytics'
const id = '11111111-1111-4111-8111-111111111111'
const platform = { period: '30d', total_gmv: '1000.20', commission_revenue: '150.03', slot_revenue: '200', total_orders: 2, new_customers: 1, active_sellers: 3, avg_order_value: '500.10', cod_rate: 50, cancellation_rate: 5 }
it('validates platform metrics and exact money formatting', () => {
  expect(validatePlatform(platform, '30d')).toBe(platform)
  expect(analyticsMoney(platform.total_gmv)).toBe('PKR 1,000.20')
  expect(() => validatePlatform({ ...platform, period: '7d' }, '30d')).toThrow()
  expect(() => validatePlatform({ ...platform, cod_rate: -1 }, '30d')).toThrow()
})
it('validates ordered revenue buckets and requested granularity', () => {
  const value = { period: '30d', granularity: 'day', data: [{ date: '2026-11-01', gross: '1000', commission: '150', net: '850', orders: 1 }] }
  expect(validateRevenue(value, '30d', 'day')).toBe(value)
  expect(() => validateRevenue(value, '30d', 'month')).toThrow()
  expect(() => validateRevenue({ ...value, data: [{ ...value.data[0], date: '2026-11-01' }, { ...value.data[0], date: '2026-11-01' }] }, '30d', 'day')).toThrow()
})
it('validates unique seller rankings and bounded response size', () => {
  const value = { period: '30d', data: [{ seller_id: id, brand_name: 'WearHowZ', logo_url: null, gmv: '1000', commission: '150', order_count: 2 }] }
  expect(validateTopSellers(value, '30d')).toBe(value)
  expect(() => validateTopSellers({ ...value, data: [{ ...value.data[0], seller_id: 'bad' }] }, '30d')).toThrow()
  expect(() => validateTopSellers({ ...value, data: [value.data[0], value.data[0]] }, '30d')).toThrow()
})
