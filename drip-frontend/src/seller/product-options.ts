import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'
import { validateEditableProduct, type EditableProduct } from './product-editor'

export interface CategoryChoice { id: string; name: string }
export interface Variant { id: string; sku: string; size_type: string; size_value: string; colour: string; price: string; stock: number; available_stock: number; is_active: boolean }
export interface OptionsProduct extends EditableProduct { category: CategoryChoice | null; variants: Variant[] }
const text = (v: unknown): v is string => typeof v === 'string' && !!v.trim()
const count = (v: unknown) => Number.isSafeInteger(v) && Number(v) >= 0
const fail = () => { throw new Error('The server returned incomplete product options.') }
export function validateCategories(value: { data: CategoryChoice[] }) {
  if (!value || !Array.isArray(value.data)) return fail()
  const ids = new Set<string>()
  for (const row of value.data) {
    if (!row || !text(row.id) || !isOrderId(row.id) || !text(row.name) || ids.has(row.id)) return fail()
    ids.add(row.id)
  }
  return value
}
export function validateVariant(row: Variant) {
  if (!row || !text(row.id) || !isOrderId(row.id) || !text(row.sku)
    || !['alpha', 'numeric', 'one_size'].includes(row.size_type) || !text(row.size_value) || !text(row.colour)
    || typeof row.price !== 'string' || !/^\d{1,6}(\.\d{1,2})?$/.test(row.price) || Number(row.price) < 100 || Number(row.price) > 500000
    || !count(row.stock) || !count(row.available_stock) || row.available_stock > row.stock || typeof row.is_active !== 'boolean') return fail()
  return row
}
export function validateOptions(value: OptionsProduct, seller: string, id: string) {
  validateEditableProduct(value, seller, id)
  if (value.category !== null) validateCategories({ data: [value.category] })
  if (!Array.isArray(value.variants)) return fail()
  const ids = new Set<string>()
  for (const row of value.variants) { validateVariant(row); if (ids.has(row.id)) return fail(); ids.add(row.id) }
  return value
}
export interface VariantDraft { size_type: string; size_value: string; colour: string; stock: string; priceMode: string; price: string; is_active: boolean }
export type VariantPayload = { size_type?: string; size_value?: string; colour?: string; stock?: number; price_override?: number | null; is_active?: boolean }
export function variantPayload(draft: VariantDraft, initial?: Variant): VariantPayload {
  const size = draft.size_value.trim(), colour = draft.colour.trim()
  if (!['alpha', 'numeric', 'one_size'].includes(draft.size_type) || !size || size.length > 10 || !colour || colour.length > 50) throw new Error('Choose a size type, size value (up to 10 characters) and colour (up to 50 characters).')
  const body: VariantPayload = {}
  for (const [key, value] of [['size_type', draft.size_type], ['size_value', size], ['colour', colour]] as const) if (!initial || initial[key] !== value) body[key] = value
  if (!initial) {
    if (!/^\d{1,10}$/.test(draft.stock) || Number(draft.stock) > 2147483647) throw new Error('Initial stock must be a whole number from 0 to 2,147,483,647.')
    body.stock = Number(draft.stock)
  } else if (draft.is_active !== initial.is_active) body.is_active = draft.is_active
  if (draft.priceMode === 'inherit') body.price_override = null
  else if (draft.priceMode === 'set') {
    if (!/^\d{1,6}$/.test(draft.price) || Number(draft.price) < 100 || Number(draft.price) > 500000) throw new Error('The override must be a whole PKR amount from 100 to 500,000.')
    body.price_override = Number(draft.price)
  } else if (draft.priceMode !== 'keep' || !initial) throw new Error('Choose a valid pricing action.')
  if (!Object.keys(body).length) throw new Error('Make a change before saving.')
  return body
}
export function confirmVariant(row: Variant, body: VariantPayload, basePrice: string, initial?: Variant) {
  validateVariant(row)
  if (initial && (row.id !== initial.id || row.sku !== initial.sku)) return fail()
  for (const key of ['size_type', 'size_value', 'colour', 'is_active'] as const) if (Object.hasOwn(body, key) && row[key] !== body[key]) return fail()
  if (Object.hasOwn(body, 'price_override') && paisa(row.price) !== paisa(String(body.price_override ?? basePrice))) return fail()
  // Stock can change concurrently after creation; it is displayed, not replayed.
  return row
}
export const variantMarker = (seller: string, product: string) => `wearhowz:variant-create-pending:${seller}:${product}`
