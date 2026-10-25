import { describe, expect, it } from 'vitest'
import { clearFilters, readFilters } from './filters'

describe('catalogue filters', () => {
  it('preserves repeated sizes and exact colour values', () => {
    const params = new URLSearchParams('size_alpha=S&size_alpha=M&colour=Ivory&min_price=0&max_price=500000&on_sale=true')
    expect(readFilters(params).get('min_price')).toBe('0')
    expect(readFilters(params).get('max_price')).toBe('500000')
    expect(readFilters(params).getAll('size_alpha')).toEqual(['S', 'M'])
    expect(readFilters(params).get('colour')).toBe('Ivory')
  })
  it.each(['min_price=-1', 'max_price=500001', 'min_price=1.5', 'min_price=20&max_price=10', 'category_id=no', 'on_sale=yes', 'max_price=10&max_price=20', 'size_alpha=12345678901'])('rejects invalid URL filters: %s', (query) => {
    expect(() => readFilters(new URLSearchParams(query))).toThrow()
  })
  it('clears filters and cursor while keeping search and sort', () => {
    expect(clearFilters(new URLSearchParams('q=linen&sort=rating&cursor=old&colour=Ivory&is_new=true')).toString()).toBe('q=linen&sort=rating')
  })
})
