import { expect, it } from 'vitest'
import { confirmModerationReceipt, confirmProductModeration, moderationImage, productListQuery, productModerationMarker, sameModerationReview, validateAdminProductDetail, validateAdminProducts, type AdminProductDetail } from './products'
const id = '11111111-1111-4111-8111-111111111111', seller = '22222222-2222-4222-8222-222222222222'
const product: AdminProductDetail = { id, seller_id: seller, name: 'Linen coat', slug: 'linen-coat', price: '1500.25', sale_price: '1200.75', description: 'An everyday coat.', meta_title: null, meta_description: null, is_published: false, admin_hidden: true, seller_status: 'suspended', seller_deleted: false, seller: { id: seller, brand_name: 'Test Label', return_policy: 'Seven days.' }, category: null, created_at: '2026-10-28T10:00:00Z', images: [], variants: [{ id, sku: 'WHZ-COAT', size_type: 'alpha', size_value: 'M', colour: 'Ivory', price: '1200.75', stock: 8, available_stock: 6, is_active: true }] }
it('builds only supported filters without inventing server search', () => {
  expect(productListQuery(seller, 'true', '2')).toBe(`page=2&seller_id=${seller}&admin_hidden=true`)
  expect(productListQuery('', 'all', '1')).toBe('page=1')
  expect(() => productListQuery('other', 'all', '1')).toThrow()
  expect(() => productListQuery('', 'all', '1e3')).toThrow()
  expect(() => productListQuery('', 'any', '1')).toThrow()
})
it('validates list scope, pagination and exact PKR strings', () => {
  const value = { data: [product], pagination: { page: 1, per_page: 25, total: 26 } }
  expect(validateAdminProducts(value, 1, seller, 'true')).toBe(value)
  expect(() => validateAdminProducts(value, 2, seller, 'true')).toThrow()
  expect(() => validateAdminProducts(value, 1, id, 'true')).toThrow()
  expect(() => validateAdminProducts(value, 1, seller, 'false')).toThrow()
  expect(() => validateAdminProducts({ ...value, data: [product, product] }, 1, seller, 'true')).toThrow()
  expect(() => validateAdminProducts({ ...value, data: [{ ...product, price: '1e3' }] }, 1, seller, 'true')).toThrow()
})
it('accepts drafts and hidden/inactive sellers without assuming public availability', () => {
  expect(validateAdminProductDetail(product, id)).toBe(product)
  expect(validateAdminProductDetail({ ...product, seller_deleted: true, seller_status: 'future_state' }, id).seller_deleted).toBe(true)
  expect(() => validateAdminProductDetail({ ...product, admin_hidden: undefined! }, id)).toThrow()
  expect(() => validateAdminProductDetail({ ...product, seller: { ...product.seller, id } }, id)).toThrow()
  expect(() => validateAdminProductDetail(product, seller)).toThrow()
  expect(() => validateAdminProductDetail({ ...product, variants: [{ ...product.variants[0], available_stock: 9 }] }, id)).toThrow()
})
it('rechecks reviewed content, variants and seller flags but tolerates live stock counts', () => {
  expect(sameModerationReview(product, { ...product, variants: [{ ...product.variants[0], stock: 7, available_stock: 5 }], seller: { ...product.seller, avg_rating: 4.5 } } as AdminProductDetail)).toBe(true)
  for (const changes of [{ admin_hidden: false }, { description: 'Changed copy' }, { seller_status: 'active' }, { is_published: true }, { variants: [{ ...product.variants[0], colour: 'Black' }] }]) expect(sameModerationReview(product, { ...product, ...changes })).toBe(false)
})
it('confirms only the requested admin flag and matching product/seller identity', () => {
  expect(confirmModerationReceipt({ id, admin_hidden: false }, id, false).admin_hidden).toBe(false)
  expect(() => confirmModerationReceipt({ id: seller, admin_hidden: false }, id, false)).toThrow()
  expect(() => confirmProductModeration(product, product, false)).toThrow()
  const saved = { ...product, admin_hidden: false }
  expect(confirmProductModeration(saved, product, false).is_published).toBe(false)
  expect(() => confirmProductModeration({ ...saved, seller_id: id, seller: { ...saved.seller, id } }, product, false)).toThrow()
})
it('never renders credential-bearing or unsafe image URLs and isolates pending markers', () => {
  expect(moderationImage('https://example.test/image.png')).toBe('https://example.test/image.png')
  for (const url of ['javascript:alert(1)', 'http://example.test/a', 'https://user:password@example.test/a']) expect(moderationImage(url)).toBeNull()
  expect(productModerationMarker('owner-a', id)).not.toBe(productModerationMarker('owner-b', id))
})
