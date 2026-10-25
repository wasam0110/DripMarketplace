export const filterKeys = ['category_id', 'min_price', 'max_price', 'size_alpha', 'size_numeric', 'colour', 'on_sale', 'is_new'] as const
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/** Validate URL and form filters equally; never silently show unfiltered results. */
export function readFilters(params: URLSearchParams): URLSearchParams {
  const result = new URLSearchParams()
  for (const key of filterKeys) {
    for (const value of params.getAll(key)) {
      if (!value) continue
      if (key === 'category_id' && !uuid.test(value)) throw new Error('Choose a valid category or clear filters.')
      if ((key === 'min_price' || key === 'max_price') && (!/^\d+$/.test(value) || Number(value) > 500000)) {
        throw new Error('Prices must be whole PKR amounts between 0 and 500,000.')
      }
      if ((key === 'on_sale' || key === 'is_new') && !['true', 'false'].includes(value)) throw new Error('Invalid sale or new-arrival filter. Clear filters to continue.')
      if ((key === 'size_alpha' || key === 'size_numeric') && value.length > 10) throw new Error('Each size must be 10 characters or fewer.')
      if (key === 'colour' && value.length > 50) throw new Error('Each colour must be 50 characters or fewer.')
      result.append(key, value)
    }
    if (!['size_alpha', 'size_numeric', 'colour'].includes(key) && result.getAll(key).length > 1) throw new Error('A filter was repeated. Clear filters to continue.')
  }
  if (result.has('min_price') && result.has('max_price') && Number(result.get('min_price')) > Number(result.get('max_price'))) {
    throw new Error('Minimum price must not exceed maximum price.')
  }
  return result
}

export function clearFilters(params: URLSearchParams) {
  const next = new URLSearchParams(params)
  for (const key of filterKeys) next.delete(key)
  next.delete('cursor')
  return next
}
