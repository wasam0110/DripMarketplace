import { isOrderId } from '../orders/api'
import { analyticsMoney, periods, type Period } from '../seller/analytics'

export { analyticsMoney, periods }
export type { Period }
export type Granularity = 'day' | 'week' | 'month'
export interface PlatformAnalytics { period: string; total_gmv: string; commission_revenue: string; slot_revenue: string; total_orders: number; new_customers: number; active_sellers: number; avg_order_value: string; cod_rate: number; cancellation_rate: number }
export interface RevenueRow { date: string; gross: string; commission: string; net: string; orders: number }
export interface RevenueSeries { period: string; granularity: string; data: RevenueRow[] }
export interface TopSeller { seller_id: string; brand_name: string; logo_url: string | null; gmv: string; commission: string; order_count: number }
export interface TopSellers { period: string; data: TopSeller[] }
const fail = (): never => { throw new Error('The admin analytics information could not be verified. Refresh to try again.') }
const count = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
const money = (value: unknown): value is string => typeof value === 'string' && /^\d{1,24}(\.\d{1,2})?$/.test(value)
const percent = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0
const day = (value: unknown): value is string => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value
export function validatePlatform(value: PlatformAnalytics, period: Period) {
  if (!value || value.period !== period || ![value.total_gmv, value.commission_revenue, value.slot_revenue, value.avg_order_value].every(money)
    || ![value.total_orders, value.new_customers, value.active_sellers].every(count) || ![value.cod_rate, value.cancellation_rate].every(percent)) return fail()
  return value
}
export function validateRevenue(value: RevenueSeries, period: Period, granularity: Granularity) {
  if (!value || value.period !== period || value.granularity !== granularity || !Array.isArray(value.data) || value.data.length > 367) return fail()
  let previous = ''
  for (const row of value.data) {
    if (!row || !day(row.date) || row.date <= previous || ![row.gross, row.commission, row.net].every(money) || !count(row.orders)) return fail()
    previous = row.date
  }
  return value
}
export function validateTopSellers(value: TopSellers, period: Period) {
  if (!value || value.period !== period || !Array.isArray(value.data) || value.data.length > 50) return fail()
  const ids = new Set<string>()
  for (const row of value.data) {
    if (!row || !isOrderId(row.seller_id) || ids.has(row.seller_id) || typeof row.brand_name !== 'string' || !row.brand_name.trim()
      || !(row.logo_url === null || typeof row.logo_url === 'string') || !money(row.gmv) || !money(row.commission) || !count(row.order_count)) return fail()
    ids.add(row.seller_id)
  }
  return value
}
