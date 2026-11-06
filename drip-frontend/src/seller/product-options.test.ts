import { expect, it } from 'vitest'
import { confirmVariant, validateCategories, validateVariant, variantPayload, type VariantDraft } from './product-options'
const row = { id: '33333333-3333-4333-8333-333333333333', sku: 'WHZ-TEST', size_type: 'alpha', size_value: 'M', colour: 'Blue', price: '2500.00', stock: 5, available_stock: 3, is_active: true }
const draft: VariantDraft = { size_type: 'alpha', size_value: 'M', colour: 'Blue', stock: '5', priceMode: 'keep', price: '', is_active: true }
it('keeps pricing and stock untouched when editing colour', () => {
  expect(variantPayload({ ...draft, colour: 'Green', stock: '100' }, row)).toEqual({ colour: 'Green' })
})
it('clears an override only through an explicit inherit action', () => {
  expect(variantPayload({ ...draft, priceMode: 'inherit' }, row)).toEqual({ price_override: null })
  expect(() => variantPayload(draft, row)).toThrow('Make a change')
})
it('creates a variant with initial stock but no invented SKU', () => {
  expect(variantPayload({ ...draft, priceMode: 'inherit' })).toEqual({ size_type: 'alpha', size_value: 'M', colour: 'Blue', stock: 5, price_override: null })
})
it.each(['99', '500001', '1e3', '2500.50'])('rejects override %s', (price) => {
  expect(() => variantPayload({ ...draft, priceMode: 'set', price }, row)).toThrow()
})
it.each(['-1', '1.5', '2147483648'])('rejects initial stock %s', (stock) => {
  expect(() => variantPayload({ ...draft, priceMode: 'inherit', stock })).toThrow()
})
it('checks response identity, changed fields and inherited effective price', () => {
  expect(confirmVariant(row, { price_override: null }, '2500', row)).toEqual(row)
  expect(() => confirmVariant(row, { colour: 'Green' }, '2500', row)).toThrow()
  expect(() => confirmVariant(row, { price_override: null }, '2000', row)).toThrow()
  expect(() => confirmVariant({ ...row, id: '44444444-4444-4444-8444-444444444444' }, {}, '2500', row)).toThrow()
})
it('rejects impossible stock, invalid categories and duplicate IDs', () => {
  expect(() => validateVariant({ ...row, available_stock: 6 })).toThrow()
  expect(() => validateCategories({ data: [{ id: 'bad', name: 'Shirts' }] })).toThrow()
  const category = { id: row.id, name: 'Shirts' }
  expect(() => validateCategories({ data: [category, category] })).toThrow()
  expect(validateCategories({ data: [] })).toEqual({ data: [] })
})
