import { expect, it } from 'vitest'
import { confirmProduct, productChanges, productDraft, validateEditableProduct } from './product-editor'
const seller = '11111111-1111-4111-8111-111111111111'
const product = { id: '22222222-2222-4222-8222-222222222222', seller_id: seller, name: 'Linen shirt', description: 'A lightweight linen shirt.', price: '2500.00', sale_price: '2000.00', meta_title: null, meta_description: null }
it('sends only changed fields and explicit null for sale removal', () => {
  expect(productChanges(productDraft(product), product)).toEqual({})
  expect(productChanges({ ...productDraft(product), sale_price: '' }, product)).toEqual({ sale_price: null })
})
it.each(['99', '500001', '1e3', '2500.50', '-100', ''])('rejects invalid regular price %s', (price) => {
  expect(() => productChanges({ ...productDraft(product), price })).toThrow()
})
it('rejects sale prices not below the regular price', () => {
  expect(() => productChanges({ ...productDraft(product), price: '2000' })).toThrow()
})
it('validates ownership and product ID', () => {
  expect(() => validateEditableProduct(product, 'other')).toThrow()
  expect(() => validateEditableProduct(product, seller, seller)).toThrow()
  expect(validateEditableProduct(product, seller, product.id)).toEqual(product)
})
it('compares decimal amounts numerically but text exactly', () => {
  expect(confirmProduct(product, seller, { price: 2500 }, product.id)).toEqual(product)
  expect(() => confirmProduct(product, seller, { name: 'Different shirt' }, product.id)).toThrow()
})
it('creates the whitelisted basic fields only', () => {
  expect(productChanges(productDraft(product))).toEqual({ name: product.name, description: product.description, price: 2500, sale_price: 2000, meta_title: null, meta_description: null })
})
