import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { Button, ErrorNotice, Field } from '../components/ui'
import { useResource } from '../hooks/useResource'
import { clearFilters, filterKeys, readFilters } from './filters'

interface Category { id: string; name: string; parent_id: string | null }
function CategorySelect({ selected, categories }: { selected: string; categories: Category[] }) {
  const [value, setValue] = useState(selected)
  return <select id="filter-category" name="category_id" value={value} onChange={(event) => setValue(event.target.value)}>
    <option value="">All categories</option>
    {value && !categories.some((item) => item.id === value) && <option value={value}>Selected category (details unavailable)</option>}
    {categories.map((item) => <option key={item.id} value={item.id}>
      {item.parent_id ? `${categories.find((parent) => parent.id === item.parent_id)?.name ?? 'Subcategory'} / ` : ''}{item.name}
    </option>)}
  </select>
}

export function Filters() {
  const [params, setParams] = useSearchParams()
  const { data, loading, error, retry } = useResource<{ data: Category[] }>('/categories')
  const [formError, setFormError] = useState<unknown>(null)
  const selected = params.get('category_id') ?? ''
  const active = filterKeys.some((key) => params.has(key))
  return <details className="catalogue-filters" open={active || undefined}>
    <summary>Refine your edit{active ? ' · Filters applied' : ''}</summary>
    <form key={params.toString()} onSubmit={(event) => {
      event.preventDefault()
      const fields = new FormData(event.currentTarget)
      const draft = new URLSearchParams()
      for (const key of filterKeys) {
        const value = String(fields.get(key) ?? '').trim()
        if (['size_alpha', 'size_numeric', 'colour'].includes(key)) {
          for (const item of [...new Set(value.split(',').map((part) => part.trim()).filter(Boolean))]) draft.append(key, item)
        } else if (value) draft.set(key, value)
      }
      try {
        const valid = readFilters(draft)
        const next = clearFilters(params)
        valid.forEach((value, key) => next.append(key, value))
        setFormError(null); setParams(next)
      } catch (failure) { setFormError(failure) }
    }}>
      <p>Choose an exact category. Parent categories do not include their subcategories automatically.</p>
      {loading && <p role="status">Loading categories…</p>}
      {Boolean(error) && <><ErrorNotice error={error} /><Button onClick={retry}>Retry categories</Button></>}
      <div className="filter-fields">
        <div className="field"><label htmlFor="filter-category">Category</label>
          <CategorySelect selected={selected} categories={data?.data ?? []} />
        </div>
        <Field label="Minimum price (PKR)" name="min_price" type="number" min="0" max="500000" step="1" defaultValue={params.get('min_price') ?? ''} />
        <Field label="Maximum price (PKR)" name="max_price" type="number" min="0" max="500000" step="1" defaultValue={params.get('max_price') ?? ''} />
        <Field label="Letter sizes" name="size_alpha" placeholder="e.g. S, M" defaultValue={params.getAll('size_alpha').join(', ')} />
        <Field label="Numeric sizes" name="size_numeric" placeholder="e.g. 30, 32" defaultValue={params.getAll('size_numeric').join(', ')} />
        <Field label="Colours" name="colour" placeholder="e.g. Black, Ivory" defaultValue={params.getAll('colour').join(', ')} />
      </div>
      <p className="muted">Separate sizes and colours with commas; use the exact labels shown on products. Matching variants may be sold out. Price filters use the product price, not variant-specific pricing.</p>
      <div className="filter-checks">
        <label><input type="checkbox" name="on_sale" value="true" defaultChecked={params.get('on_sale') === 'true'} /> On sale</label>
        <label><input type="checkbox" name="is_new" value="true" defaultChecked={params.get('is_new') === 'true'} /> Added in the last 14 days</label>
      </div>
      {Boolean(formError) && <ErrorNotice error={formError} />}
      <div className="filter-actions"><Button type="submit">Apply filters</Button>
        <Button className="button-secondary" onClick={() => { setFormError(null); setParams(clearFilters(params)) }}>Clear filters</Button></div>
    </form>
  </details>
}
