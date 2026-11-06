import { expect, it } from 'vitest'
import { confirmStock, stockCommand, validateInventory, validateStock } from './inventory'
const row = { variant_id: '33333333-3333-4333-8333-333333333333', product_id: '22222222-2222-4222-8222-222222222222', product_name: 'Linen shirt', sku: 'WHZ-TEST', size: 'M', colour: 'Blue', stock: 10, reserved: 3, available: 7, reorder_point: 5, is_low_stock: false, last_restocked_at: null }
it('validates reservation arithmetic and low stock from available units', () => {
  expect(validateStock(row)).toEqual(row)
  expect(() => validateStock({ ...row, available: 10 })).toThrow()
  expect(() => validateStock({ ...row, reserved: 11 })).toThrow()
  expect(() => validateStock({ ...row, is_low_stock: true })).toThrow()
})
it('requires selected variant and product identities', () => {
  expect(() => validateStock(row, row.product_id)).toThrow()
  expect(() => validateStock(row, row.variant_id, row.variant_id)).toThrow()
})
it('validates pagination and duplicate variants', () => {
  const page = { data: [row], total: 1, page: 1, per_page: 20, pages: 1 }
  expect(validateInventory(page, 1, false)).toEqual(page)
  expect(() => validateInventory(page, 2, false)).toThrow()
  expect(() => validateInventory(page, 1, true)).toThrow()
  expect(() => validateInventory({ ...page, data: [row, row], total: 2 }, 1, false)).toThrow()
})
it.each(['0', '10001', '-10001', '1e3', '1.5', ''])('rejects invalid adjustment %s', (quantity) => {
  expect(() => stockCommand('adjust', quantity, 'Restock', '5', row)).toThrow()
})
it('protects reserved units and trims the reason', () => {
  expect(stockCommand('adjust', '-7', '  Damaged goods  ', '5', row)).toEqual({ kind: 'adjust', body: { delta: -7, reason: 'Damaged goods' } })
  expect(() => stockCommand('adjust', '-8', 'Damaged goods', '5', row)).toThrow()
  expect(() => stockCommand('adjust', '2', '   ', '5', row)).toThrow()
})
it('requires a physical count and only sends an explicitly changed threshold', () => {
  expect(stockCommand('set', '15', '', '5', row)).toEqual({ kind: 'set', body: { stock: 15 } })
  expect(stockCommand('set', '15', '', '6', row)).toEqual({ kind: 'set', body: { stock: 15, reorder_point: 6 } })
  expect(() => stockCommand('set', '2', '', '5', row)).toThrow()
  expect(() => stockCommand('set', '1000000', '', '5', row)).toThrow()
  expect(() => stockCommand('set', '10', '', '5', row)).toThrow()
})
it('uses the server adjustment receipt when another operation changed stock', () => {
  const command = stockCommand('adjust', '5', 'Restock', '5', row)
  expect(confirmStock({ variant_id: row.variant_id, previous_stock: 8, new_stock: 13, delta: 5, reason: 'Restock' }, command, row)).toContain('8 → 13')
})
it('rejects mismatched receipts instead of replaying a delta', () => {
  const receipt = { variant_id: row.variant_id, previous_stock: 10, new_stock: 15, delta: 5, reason: 'Restock' }
  const command = stockCommand('adjust', '5', 'Restock', '5', row)
  expect(() => confirmStock({ ...receipt, new_stock: 20 }, command, row)).toThrow()
  expect(() => confirmStock({ ...receipt, variant_id: row.product_id }, command, row)).toThrow()
  expect(() => confirmStock({ ...receipt, delta: 10 }, command, row)).toThrow()
})
it('confirms the requested count without asserting an untouched threshold', () => {
  const saved = { ...row, stock: 15, available: 12, reorder_point: 7 }
  expect(confirmStock(saved, { kind: 'set', body: { stock: 15 } }, row)).toContain('15 units')
  expect(() => confirmStock(saved, { kind: 'set', body: { stock: 15, reorder_point: 6 } }, row)).toThrow()
})
