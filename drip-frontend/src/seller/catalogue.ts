import { isOrderId } from '../orders/api'

export interface SellerProductRow {
  id: string; name: string; category: string | null; price: string
  total_stock: number; is_published: boolean; image_count: number
}
export interface SellerCatalogue {
  data: SellerProductRow[]
  slot_info: { total_slots: number; slots_used: number; slots_available: number }
}
const count = (value: unknown) => Number.isSafeInteger(value) && (value as number) >= 0
/** Reject incomplete private responses instead of presenting invented stock or capacity. */
export function validateSellerCatalogue(value: SellerCatalogue): SellerCatalogue {
  const fail = () => { throw new Error('The server returned incomplete catalogue information. Refresh to try again.') }
  if (!value || !Array.isArray(value.data) || value.data.length > 20 || !value.slot_info) return fail()
  const slots = value.slot_info
  if (![slots.total_slots, slots.slots_used, slots.slots_available].every(count)) return fail()
  const ids = new Set<string>()
  const data = value.data.map((row) => {
    if (!row || typeof row.id !== 'string' || !isOrderId(row.id) || ids.has(row.id)
      || typeof row.name !== 'string' || !row.name.trim()
      || !(row.category === null || typeof row.category === 'string')
      || typeof row.price !== 'string' || !/^\d{1,10}(\.\d{1,2})?$/.test(row.price)
      || !count(row.total_stock) || !count(row.image_count) || typeof row.is_published !== 'boolean') return fail()
    ids.add(row.id)
    return { id: row.id, name: row.name, category: row.category, price: row.price,
      total_stock: row.total_stock, image_count: row.image_count, is_published: row.is_published }
  })
  return { data, slot_info: { ...slots } }
}
