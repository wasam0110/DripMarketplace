import { isOrderId } from '../orders/api'
import { paisa } from '../checkout/preview'

export const productFields = ['name', 'description', 'price', 'sale_price', 'meta_title', 'meta_description'] as const
export type ProductDraft = Record<typeof productFields[number], string>
export interface EditableProduct {
  id: string; seller_id: string; name: string; description: string | null
  price: string; sale_price: string | null; meta_title: string | null; meta_description: string | null
}
export type ProductChanges = Partial<Record<typeof productFields[number], string | number | null>>
export const emptyProduct: ProductDraft = { name: '', description: '', price: '', sale_price: '', meta_title: '', meta_description: '' }
export const creationMarker = (sellerId: string) => `wearhowz:product-create-pending:${sellerId}`
export function validateEditableProduct(value: EditableProduct, sellerId: string, productId?: string): EditableProduct {
  if (!value || typeof value.id !== 'string' || !isOrderId(value.id) || (productId && value.id !== productId)
    || value.seller_id !== sellerId || typeof value.name !== 'string' || !value.name.trim()
    || ![value.description, value.meta_title, value.meta_description].every((v) => v === null || typeof v === 'string')
    || ![value.price, ...(value.sale_price === null ? [] : [value.sale_price])].every((v) => typeof v === 'string' && /^\d{1,6}(\.\d{1,2})?$/.test(v))
    || Number(value.price) < 100 || Number(value.price) > 500000
    || (value.sale_price !== null && (Number(value.sale_price) < 100 || Number(value.sale_price) >= Number(value.price)))) {
    throw new Error('The product identity or details could not be verified.')
  }
  return value
}
export function productDraft(value: EditableProduct): ProductDraft {
  return { name: value.name, description: value.description ?? '', price: value.price.replace(/\.00$/, ''),
    sale_price: value.sale_price?.replace(/\.00$/, '') ?? '', meta_title: value.meta_title ?? '', meta_description: value.meta_description ?? '' }
}
export function productChanges(draft: ProductDraft, initial?: EditableProduct): ProductChanges {
  const value = { ...draft, name: draft.name.trim(), description: draft.description.trim() }
  if (value.name.length < 2 || value.name.length > 200 || value.description.length < 10 || value.description.length > 5000) throw new Error('Use a name of 2–200 characters and description of 10–5000 characters.')
  const price = (raw: string) => {
    if (!/^\d{1,6}$/.test(raw) || Number(raw) < 100 || Number(raw) > 500000) throw new Error('Prices must be whole PKR amounts from 100 to 500,000.')
    return Number(raw)
  }
  const regular = price(value.price), sale = value.sale_price === '' ? null : price(value.sale_price)
  if (sale !== null && sale >= regular) throw new Error('Sale price must be below the regular price.')
  if (value.meta_title.length > 200 || value.meta_description.length > 500) throw new Error('SEO title is limited to 200 characters and description to 500.')
  const candidate = { ...value, price: regular, sale_price: sale, meta_title: value.meta_title || null, meta_description: value.meta_description || null }
  const changes: ProductChanges = {}
  for (const key of productFields) {
    const before = initial?.[key], after = candidate[key]
    const same = initial && (key === 'price' || key === 'sale_price')
      ? (before === null || after === null ? before === after : paisa(String(before)) === paisa(String(after)))
      : initial && before === after
    if (!same) changes[key] = after
  }
  return changes
}
export function confirmProduct(value: EditableProduct, sellerId: string, changes: ProductChanges, productId?: string) {
  const result = validateEditableProduct(value, sellerId, productId)
  for (const key of productFields) {
    if (!Object.hasOwn(changes, key)) continue
    const expected = changes[key], actual = result[key]
    const same = (key === 'price' || key === 'sale_price') && expected !== null && actual !== null
      ? paisa(String(expected)) === paisa(String(actual)) : actual === expected
    if (!same) throw new Error('The saved product did not match the requested changes. Inspect it before retrying.')
  }
  return result
}
