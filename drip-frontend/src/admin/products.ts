import { isOrderId } from '../orders/api'
import { safeAvatarUrl } from '../account/avatar'

export interface AdminProductRow { id: string; seller_id: string; name: string; slug: string; price: string; is_published: boolean; admin_hidden: boolean }
export interface AdminProductPage { data: AdminProductRow[]; pagination: { page: number; per_page: number; total: number } }
export interface AdminProductDetail extends AdminProductRow {
  sale_price: string | null; description: string | null; meta_title: string | null; meta_description: string | null
  seller_status: string; seller_deleted: boolean; seller: { id: string; brand_name: string; return_policy: string | null }
  category: { id: string; name: string } | null; created_at: string
  images: { id: string; url: string; alt_text: string | null; sort_order: number; is_primary: boolean }[]
  variants: { id: string; sku: string; size_type: string; size_value: string; colour: string; price: string; stock: number; available_stock: number; is_active: boolean }[]
}
const fail = (): never => { throw new Error('Product moderation information could not be verified. Refresh to try again.') }
const text = (v: unknown): v is string => typeof v === 'string' && !!v.trim()
const uuid = (v: unknown) => text(v) && isOrderId(v)
const money = (v: unknown) => typeof v === 'string' && /^\d{1,12}(\.\d{1,2})?$/.test(v)
const count = (v: unknown): v is number => Number.isSafeInteger(v) && (v as number) >= 0
const nullableText = (v: unknown) => v === null || typeof v === 'string'
export function productListQuery(seller: string, hidden: string, page: string) {
  const id = seller.trim()
  if (id && !isOrderId(id)) throw new Error('Enter a valid seller reference or leave it blank for all sellers.')
  if (!['all', 'true', 'false'].includes(hidden) || !/^[1-9]\d*$/.test(page) || !Number.isSafeInteger(Number(page))) throw new Error('Choose valid product filters and a positive page number.')
  const params = new URLSearchParams({ page })
  if (id) params.set('seller_id', id)
  if (hidden !== 'all') params.set('admin_hidden', hidden)
  return params.toString()
}
export function validateAdminProduct(row: AdminProductRow) {
  if (!row || !uuid(row.id) || !uuid(row.seller_id) || !text(row.name) || !text(row.slug) || !money(row.price) || typeof row.is_published !== 'boolean' || typeof row.admin_hidden !== 'boolean') return fail()
  return row
}
export function validateAdminProducts(value: AdminProductPage, page: number, seller: string, hidden: string) {
  if (!value || !Array.isArray(value.data) || !value.pagination || value.pagination.page !== page || value.pagination.per_page !== 25 || !count(value.pagination.total) || value.data.length > 25 || value.data.length > value.pagination.total) return fail()
  const ids = new Set<string>()
  for (const row of value.data) { validateAdminProduct(row); if (ids.has(row.id) || (seller && row.seller_id !== seller) || (hidden !== 'all' && row.admin_hidden !== (hidden === 'true'))) return fail(); ids.add(row.id) }
  return value
}
export function validateAdminProductDetail(value: AdminProductDetail, id: string) {
  validateAdminProduct(value)
  if (value.id !== id || ![value.description, value.meta_title, value.meta_description].every(nullableText) || !(value.sale_price === null || money(value.sale_price))
    || !text(value.seller_status) || typeof value.seller_deleted !== 'boolean' || !value.seller || value.seller.id !== value.seller_id || !text(value.seller.brand_name) || !nullableText(value.seller.return_policy)
    || !(value.category === null || (value.category && uuid(value.category.id) && text(value.category.name)))
    || !text(value.created_at) || !/^\d{4}-\d{2}-\d{2}T/.test(value.created_at) || !Number.isFinite(Date.parse(value.created_at)) || !Array.isArray(value.images) || !Array.isArray(value.variants)) return fail()
  const images = new Set<string>(), variants = new Set<string>()
  for (const row of value.images) { if (!row || !uuid(row.id) || images.has(row.id) || typeof row.url !== 'string' || !nullableText(row.alt_text) || !count(row.sort_order) || typeof row.is_primary !== 'boolean') return fail(); images.add(row.id) }
  for (const row of value.variants) { if (!row || !uuid(row.id) || variants.has(row.id) || ![row.sku, row.size_type, row.size_value, row.colour].every(text) || !money(row.price) || !count(row.stock) || !count(row.available_stock) || row.available_stock > row.stock || typeof row.is_active !== 'boolean') return fail(); variants.add(row.id) }
  return value
}
/** Exclude volatile stock/rating counts, but recheck the content actually reviewed. */
export function sameModerationReview(before: AdminProductDetail, latest: AdminProductDetail) {
  const snapshot = (row: AdminProductDetail) => ({ id: row.id, seller_id: row.seller_id, name: row.name, slug: row.slug, price: row.price, sale_price: row.sale_price, description: row.description, meta_title: row.meta_title, meta_description: row.meta_description, is_published: row.is_published, admin_hidden: row.admin_hidden, seller_status: row.seller_status, seller_deleted: row.seller_deleted, seller: { id: row.seller.id, brand_name: row.seller.brand_name, return_policy: row.seller.return_policy },
    category: row.category, images: [...row.images].sort((a, b) => a.id.localeCompare(b.id)), variants: row.variants.map(({ stock: _stock, available_stock: _available, ...variant }) => variant).sort((a, b) => a.id.localeCompare(b.id)) })
  return JSON.stringify(snapshot(before)) === JSON.stringify(snapshot(latest))
}
export function confirmProductModeration(value: AdminProductDetail, before: AdminProductDetail, hidden: boolean) {
  validateAdminProductDetail(value, before.id)
  if (value.seller_id !== before.seller_id || value.admin_hidden !== hidden) return fail()
  return value
}
export function confirmModerationReceipt(value: { id: string; admin_hidden: boolean }, id: string, hidden: boolean) {
  if (!value || value.id !== id || value.admin_hidden !== hidden) return fail()
  return value
}
export const productModerationMarker = (owner: string, id: string) => `wearhowz:admin-product-pending:${owner}:${id}`
export function moderationImage(url: string) { try { return safeAvatarUrl(url) } catch { return null } }
