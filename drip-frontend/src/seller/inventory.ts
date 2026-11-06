import { isOrderId } from '../orders/api'

export interface StockRow {
  variant_id: string; product_id: string; product_name: string; sku: string | null; size: string | null; colour: string | null
  stock: number; reserved: number; available: number; reorder_point: number; is_low_stock: boolean; last_restocked_at: string | null
}
export interface InventoryPage { data: StockRow[]; total: number; page: number; per_page: number; pages: number }
export type StockCommand = { kind: 'adjust'; body: { delta: number; reason: string } } | { kind: 'set'; body: { stock: number; reorder_point?: number } }
export interface AdjustmentReceipt { variant_id: string; previous_stock: number; new_stock: number; delta: number; reason: string }
const count = (v: unknown) => Number.isSafeInteger(v) && Number(v) >= 0 && Number(v) <= 2147483647
const fail = () => { throw new Error('Inventory information could not be verified. Refresh and try again.') }
export function validateStock(row: StockRow, variantId?: string, productId?: string): StockRow {
  if (!row || typeof row.variant_id !== 'string' || !isOrderId(row.variant_id) || typeof row.product_id !== 'string' || !isOrderId(row.product_id)
    || (variantId && row.variant_id !== variantId) || (productId && row.product_id !== productId)
    || typeof row.product_name !== 'string' || !row.product_name.trim()
    || ![row.sku, row.size, row.colour, row.last_restocked_at].every((v) => v === null || typeof v === 'string')
    || ![row.stock, row.reserved, row.available, row.reorder_point].every(count) || row.reserved > row.stock
    || row.available !== row.stock - row.reserved || row.is_low_stock !== (row.available <= row.reorder_point)) return fail()
  return row
}
export function validateInventory(value: InventoryPage, page: number, lowOnly: boolean): InventoryPage {
  if (!value || !Array.isArray(value.data) || value.page !== page || value.per_page !== 20 || !count(value.total)
    || value.pages !== Math.ceil(value.total / 20) || value.data.length > 20 || value.data.length > value.total) return fail()
  const ids = new Set<string>()
  for (const row of value.data) { validateStock(row); if (ids.has(row.variant_id) || (lowOnly && !row.is_low_stock)) return fail(); ids.add(row.variant_id) }
  return value
}
export function stockCommand(mode: 'adjust' | 'set', quantity: string, reason: string, reorder: string, snapshot: StockRow): StockCommand {
  if (mode === 'adjust') {
    if (!/^[+-]?\d{1,5}$/.test(quantity) || Number(quantity) === 0 || Math.abs(Number(quantity)) > 10000) throw new Error('Enter a change from −10,000 to +10,000 units, excluding zero.')
    const text = reason.trim()
    if (text.length < 3 || text.length > 200) throw new Error('Enter a reason of 3–200 characters.')
    if (snapshot.stock + Number(quantity) < snapshot.reserved) throw new Error('This change would reduce stock below the reserved quantity. Refresh the stock details.')
    if (snapshot.stock + Number(quantity) > 2147483647) throw new Error('The resulting quantity is too large.')
    return { kind: 'adjust', body: { delta: Number(quantity), reason: text } }
  }
  if (!/^\d{1,6}$/.test(quantity)) throw new Error('Enter the total physical stock from 0 to 999,999 units.')
  if (!/^\d{1,6}$/.test(reorder)) throw new Error('Enter a low-stock threshold from 0 to 999,999 units.')
  if (Number(quantity) < snapshot.reserved) throw new Error('Total stock cannot be below the reserved quantity. Refresh the stock details.')
  const body: { stock: number; reorder_point?: number } = { stock: Number(quantity) }
  if (Number(reorder) !== snapshot.reorder_point) body.reorder_point = Number(reorder)
  if (body.stock === snapshot.stock && body.reorder_point === undefined) throw new Error('Enter a changed stock count or threshold.')
  return { kind: 'set', body }
}
export function confirmStock(value: StockRow | AdjustmentReceipt, command: StockCommand, before: StockRow): string {
  if (command.kind === 'set') {
    const saved = validateStock(value as StockRow, before.variant_id, before.product_id)
    if (saved.stock !== command.body.stock || (command.body.reorder_point !== undefined && saved.reorder_point !== command.body.reorder_point)) return fail()
    return `Stock count saved: ${saved.stock} units.`
  }
  const result = value as AdjustmentReceipt
  if (!result || result.variant_id !== before.variant_id || result.delta !== command.body.delta || result.reason !== command.body.reason
    || !count(result.previous_stock) || !count(result.new_stock) || result.previous_stock + result.delta !== result.new_stock) return fail()
  // A concurrent sale or restock can change the server's previous quantity.
  return `Stock adjustment saved: ${result.previous_stock} → ${result.new_stock} units.`
}
export const inventoryMarker = (owner: string) => `wearhowz:inventory-pending:${owner}`
