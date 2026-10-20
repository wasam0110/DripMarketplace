import { describe, expect, it } from 'vitest'
import { changeGuestQuantity, GUEST_CART_KEY, parseGuestBag, readGuestBag, remainingAfterMerge, writeGuestBag } from './guestStorage'

const item = { product_id: '11111111-1111-4111-8111-111111111111', variant_id: '22222222-2222-4222-8222-222222222222', quantity: 2 }
describe('guest bag storage', () => {
  it('persists only validated selections and removes empty storage', () => {
    writeGuestBag([item])
    expect(readGuestBag()).toEqual([item])
    writeGuestBag([])
    expect(localStorage.getItem(GUEST_CART_KEY)).toBeNull()
  })
  it.each([0, 101, 1.5, '2', null])('rejects invalid quantity %s', (quantity) => {
    expect(() => parseGuestBag(JSON.stringify([{ ...item, quantity }]))).toThrow()
  })
  it('rejects duplicate variants and invalid IDs', () => {
    expect(() => parseGuestBag(JSON.stringify([item, item]))).toThrow()
    expect(() => parseGuestBag(JSON.stringify([{ ...item, product_id: 'bad' }]))).toThrow()
  })
  it('preserves corrupt storage until the user clears it', () => {
    localStorage.setItem(GUEST_CART_KEY, 'broken')
    expect(readGuestBag).toThrow()
    expect(localStorage.getItem(GUEST_CART_KEY)).toBe('broken')
  })
  it('does not trust saved prices or extra fields', () => {
    expect(parseGuestBag(JSON.stringify([{ ...item, price: 1, token: 'ignored' }]))).toEqual([item])
  })
  it('updates absolutely and removes with zero', () => {
    expect(changeGuestQuantity([item], item, 3)).toEqual([{ ...item, quantity: 3 }])
    expect(changeGuestQuantity([item], item, 0)).toEqual([])
  })
  it('only clears accepted selections unchanged during merging', () => {
    expect(remainingAfterMerge([item], [item], new Set([item.variant_id]))).toEqual([])
    expect(remainingAfterMerge([{ ...item, quantity: 3 }], [item], new Set([item.variant_id]))).toHaveLength(1)
    expect(remainingAfterMerge([item], [item], new Set())).toHaveLength(1)
  })
})
