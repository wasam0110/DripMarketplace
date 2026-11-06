import { expect, it } from 'vitest'
import { validateSellerCatalogue, type SellerCatalogue } from './catalogue'
const row = { id: '11111111-1111-4111-8111-111111111111', name: 'Linen shirt', category: null, price: '2500.00', total_stock: 0, image_count: 0, is_published: false }
const fixture = () => ({ data: [{ ...row }], slot_info: { total_slots: 10, slots_used: 1, slots_available: 9 } })
it('accepts zero stock, draft products and an empty catalogue', () => {
  expect(validateSellerCatalogue(fixture()).data[0]).toEqual(row)
  expect(validateSellerCatalogue({ ...fixture(), data: [] }).data).toEqual([])
})
it.each([{ id: 'bad' }, { name: '' }, { price: 2500 }, { price: '-1' }, { total_stock: -1 }, { image_count: 0.5 }, { is_published: 'false' }, { category: {} }])('rejects malformed fields %j', (patch) => {
  expect(() => validateSellerCatalogue({ ...fixture(), data: [{ ...row, ...patch }] } as SellerCatalogue)).toThrow()
})
it('rejects duplicate IDs, oversized pages and invalid capacity', () => {
  expect(() => validateSellerCatalogue({ ...fixture(), data: [row, row] })).toThrow()
  expect(() => validateSellerCatalogue({ ...fixture(), data: Array(21).fill(row) })).toThrow()
  expect(() => validateSellerCatalogue({ ...fixture(), slot_info: { total_slots: -1, slots_used: 0, slots_available: 0 } })).toThrow()
})
