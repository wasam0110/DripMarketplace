import { paisa } from '../checkout/preview'
import { isOrderId } from '../orders/api'

export const periods = ['7d', '30d', '90d', '1y'] as const
export type Period = typeof periods[number]
export type Granularity = 'day' | 'week' | 'month'
export type Ranking = 'revenue' | 'units' | 'views'
export interface Overview { period: string; gross_revenue: string; commission_paid: string; net_earnings: string; order_count: number; units_sold: number; avg_order_value: string; total_views: number; conversion_rate: number }
export interface RevenueRow { date: string; gross: string; commission: string; net: string; orders: number }
export interface RevenueSeries { period: string; granularity: string; data: RevenueRow[] }
export interface TopProduct { product_id: string; product_name: string; revenue: string; units_sold: number; views: number; avg_rating: number }
export interface TopProducts { period: string; sort_by: string; data: TopProduct[] }
export interface InventoryHealth { total_variants: number; in_stock: number; low_stock: number; out_of_stock: number; total_units: number }
export interface CommissionEntry {
  id: string; seller_order_id: string; commission_rate: number; settled_at: string; released_at: string | null
  gross_amount: string; commission_amount: string; seller_amount: string
  original_gross_amount: string; original_commission_amount: string; original_seller_amount: string
  refunded_gross_amount: string; reversed_commission_amount: string; reversed_seller_amount: string
  recovered_seller_amount: string; settlement_offset_amount: string; platform_shortfall_amount: string
}
export interface CommissionSummary {
  total_gross: string; total_commission: string; total_net: string
  original_gross: string; original_commission: string; original_net: string
  total_refunded_gross: string; total_reversed_commission: string; total_reversed_seller: string
  total_recovered_seller: string; total_settlement_offset: string; total_platform_shortfall: string
}
export interface CommissionPage { data: CommissionEntry[]; summary: CommissionSummary; total: number; page: number }
const fail = (): never => { throw new Error('The analytics information could not be verified. Refresh to try again.') }
const count = (v: unknown): v is number => Number.isSafeInteger(v) && (v as number) >= 0
const money = (v: unknown): v is string => typeof v === 'string' && /^\d{1,24}(\.\d{1,2})?$/.test(v)
const uuid = (v: unknown) => typeof v === 'string' && isOrderId(v)
const date = (v: unknown) => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(v) && Number.isFinite(Date.parse(v))
const day = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0, 10) === v
const balanced = (gross: string, commission: string, net: string) => paisa(gross) === paisa(commission) + paisa(net)
/** Formatting and validation never round aggregate money through JavaScript Number. */
export function analyticsMoney(value: string) {
  if (!money(value)) return fail()
  const units = paisa(value)
  return `PKR ${(units / 100n).toLocaleString('en-PK')}.${String(units % 100n).padStart(2, '0')}`
}
export function validateOverview(value: Overview, period: Period) {
  if (!value || value.period !== period || ![value.gross_revenue, value.commission_paid, value.net_earnings, value.avg_order_value].every(money)
    || ![value.order_count, value.units_sold, value.total_views].every(count) || typeof value.conversion_rate !== 'number' || !Number.isFinite(value.conversion_rate) || value.conversion_rate < 0
    || !balanced(value.gross_revenue, value.commission_paid, value.net_earnings)) return fail()
  return value
}
export function validateRevenue(value: RevenueSeries, period: Period, granularity: Granularity) {
  if (!value || value.period !== period || value.granularity !== granularity || !Array.isArray(value.data) || value.data.length > 367) return fail()
  let previous = ''
  for (const row of value.data) {
    if (!row || !day(row.date) || row.date <= previous || ![row.gross, row.commission, row.net].every(money) || !count(row.orders) || !balanced(row.gross, row.commission, row.net)) return fail()
    previous = row.date
  }
  return value
}
export function validateTopProducts(value: TopProducts, period: Period, ranking: Ranking) {
  if (!value || value.period !== period || value.sort_by !== ranking || !Array.isArray(value.data) || value.data.length > 10) return fail()
  const ids = new Set<string>()
  for (const row of value.data) {
    if (!row || !uuid(row.product_id) || ids.has(row.product_id) || typeof row.product_name !== 'string' || !row.product_name.trim() || !money(row.revenue)
      || !count(row.units_sold) || !count(row.views) || typeof row.avg_rating !== 'number' || !Number.isFinite(row.avg_rating) || row.avg_rating < 0 || row.avg_rating > 5) return fail()
    ids.add(row.product_id)
  }
  return value
}
export function validateInventoryHealth(value: InventoryHealth) {
  if (!value || ![value.total_variants, value.in_stock, value.low_stock, value.out_of_stock, value.total_units].every(count)
    || value.in_stock + value.out_of_stock !== value.total_variants || value.low_stock > value.in_stock) return fail()
  return value
}
export function validateCommissionEntry(row: CommissionEntry) {
  if (!row || !uuid(row.id) || !uuid(row.seller_order_id) || !date(row.settled_at) || !(row.released_at === null || date(row.released_at))
    || typeof row.commission_rate !== 'number' || !Number.isFinite(row.commission_rate) || row.commission_rate < 0 || row.commission_rate > 1
    || ![row.gross_amount, row.commission_amount, row.seller_amount, row.original_gross_amount, row.original_commission_amount, row.original_seller_amount,
      row.refunded_gross_amount, row.reversed_commission_amount, row.reversed_seller_amount, row.recovered_seller_amount, row.settlement_offset_amount, row.platform_shortfall_amount].every(money)) return fail()
  if (!balanced(row.original_gross_amount, row.original_commission_amount, row.original_seller_amount) || !balanced(row.gross_amount, row.commission_amount, row.seller_amount)
    || paisa(row.original_gross_amount) !== paisa(row.gross_amount) + paisa(row.refunded_gross_amount)
    || paisa(row.original_commission_amount) !== paisa(row.commission_amount) + paisa(row.reversed_commission_amount)
    || paisa(row.original_seller_amount) !== paisa(row.seller_amount) + paisa(row.reversed_seller_amount)) return fail()
  return row
}
export function validateCommission(value: CommissionPage, page: number) {
  if (!value || value.page !== page || !count(value.total) || !Array.isArray(value.data) || value.data.length > 25 || value.data.length > value.total || !value.summary) return fail()
  const summary = value.summary
  if (![summary.total_gross, summary.total_commission, summary.total_net, summary.original_gross, summary.original_commission, summary.original_net,
    summary.total_refunded_gross, summary.total_reversed_commission, summary.total_reversed_seller, summary.total_recovered_seller, summary.total_settlement_offset, summary.total_platform_shortfall].every(money)
    || !balanced(summary.total_gross, summary.total_commission, summary.total_net) || !balanced(summary.original_gross, summary.original_commission, summary.original_net)
    || paisa(summary.original_gross) !== paisa(summary.total_gross) + paisa(summary.total_refunded_gross)
    || paisa(summary.original_commission) !== paisa(summary.total_commission) + paisa(summary.total_reversed_commission)
    || paisa(summary.original_net) !== paisa(summary.total_net) + paisa(summary.total_reversed_seller)) return fail()
  const ids = new Set<string>(), orders = new Set<string>()
  for (const row of value.data) { validateCommissionEntry(row); if (ids.has(row.id) || orders.has(row.seller_order_id)) return fail(); ids.add(row.id); orders.add(row.seller_order_id) }
  return value
}
