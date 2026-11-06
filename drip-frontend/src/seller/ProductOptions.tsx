import { useCallback, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { Button, ErrorNotice, Field } from '../components/ui'
import { useOrderRead } from '../orders/api'
import { confirmVariant, validateCategories, validateOptions, variantMarker, variantPayload, type CategoryChoice, type OptionsProduct, type Variant, type VariantDraft, type VariantPayload } from './product-options'

export function ProductOptions({ sellerId, productId }: { sellerId: string; productId: string }) {
  const validate = useCallback((value: OptionsProduct) => validateOptions(value, sellerId, productId), [sellerId, productId])
  const resource = useOrderRead(`/seller/products/${productId}`, true, validate)
  const categories = useOrderRead('/categories', false, validateCategories)
  const write = useAccountWrite()
  const [editing, setEditing] = useState<Variant | 'new' | null>(null)
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(variantMarker(sellerId, productId)) !== null } catch { return true } })
  const disabled = write.busy || write.blocked || resource.loading || !resource.data
  const refresh = () => { setEditing(null); resource.retry() }
  function saveVariant(body: VariantPayload) {
    if (disabled || !editing || !resource.data || (editing === 'new' && pending)) return
    const initial = editing === 'new' ? undefined : editing
    const before = resource.data
    void write.run(async () => {
      if (!initial) { sessionStorage.setItem(variantMarker(sellerId, productId), 'pending'); setPending(true) }
      let response: OptionsProduct | Variant
      try {
        response = await request<OptionsProduct | Variant>(`/seller/products/${productId}/variants${initial ? `/${initial.id}` : ''}`, { authenticated: true, method: initial ? 'PATCH' : 'POST', body: JSON.stringify(body) })
      } catch (reason) {
        if (!initial && reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(variantMarker(sellerId, productId)); setPending(false) }
        throw reason
      }
      const base = before.sale_price ?? before.price
      if (initial) confirmVariant(response as Variant, body, base, initial)
      else {
        const result = validate(response as OptionsProduct)
        const added = result.variants.filter((row) => !before.variants.some((old) => old.id === row.id))
        if (added.length !== 1) throw new Error('The new variant could not be identified. Inspect the product before retrying.')
        confirmVariant(added[0], body, base)
        sessionStorage.removeItem(variantMarker(sellerId, productId)); setPending(false)
      }
    }, refresh, 'Variant saved and confirmed.')
  }
  return <>
    <p><Link className="text-link" to={`/seller/products/${productId}/edit`}>Edit basic product details</Link></p>
    <p><Link className="text-link" to={`/seller/products/${productId}/media`}>Manage images and publishing</Link></p>
    <p>Changes can affect a live listing immediately. Existing stock adjustments are separate. Avoid concurrent editing in other tabs.</p>
    {resource.loading && <p role="status">Loading product options…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    <WriteFeedback state={write} />
    {pending && <p role="alert">A variant creation is pending confirmation in this tab. Inspect saved variants or contact support before adding another; reloading does not clear this safeguard.</p>}
    {resource.data && <>
      <h2>{resource.data.name}</h2>
      <section className="account-card"><h3>Category</h3>
        <p>Saved category: {resource.data.category?.name ?? 'Uncategorized'}</p>
        {categories.loading && <p role="status">Loading available categories…</p>}{Boolean(categories.error) && <ErrorNotice error={categories.error} />}
        {categories.data && <CategoryForm key={JSON.stringify(resource.data.category)} current={resource.data.category} choices={categories.data.data} disabled={disabled} save={(categoryId) => {
          if (disabled) return
          void write.run(async () => {
            const result = validate(await request<OptionsProduct>(`/seller/products/${productId}`, { authenticated: true, method: 'PUT', body: JSON.stringify({ category_id: categoryId }) }))
            if ((result.category?.id ?? null) !== categoryId) throw new Error('The category change could not be confirmed.')
          }, refresh, 'Category saved and confirmed.')
        }} />}
        <Button className="button-secondary" disabled={categories.loading || write.busy} onClick={categories.retry}>Refresh available categories</Button>
      </section>
      <section aria-label="Product variants"><h3>Variants</h3>
        {!resource.data.variants.length && <p>No variants saved.</p>}
        {resource.data.variants.map((row) => <article className="account-card" key={row.id} style={{ overflowWrap: 'anywhere' }}>
          <h4>{row.size_value} · {row.colour}</h4><p>SKU: {row.sku} · {row.is_active ? 'Active' : 'Inactive'}</p>
          <dl><dt>Effective price (PKR)</dt><dd>{row.price}</dd><dt>Recorded stock</dt><dd>{row.stock}</dd><dt>Available stock</dt><dd>{row.available_stock}</dd></dl>
          <Button className="button-secondary" disabled={disabled} onClick={() => setEditing(row)}>Edit variant {row.sku}</Button>
        </article>)}
        <Button disabled={disabled || pending} onClick={() => setEditing('new')}>Add variant</Button>
      </section>
      {editing && <VariantForm key={editing === 'new' ? 'new' : editing.id} initial={editing === 'new' ? undefined : editing} disabled={disabled || (editing === 'new' && pending)} save={saveVariant} cancel={() => setEditing(null)} />}
    </>}
    <Button className="button-secondary" disabled={resource.loading || write.busy} onClick={refresh}>Refresh saved options and discard edits</Button>
    <p className="muted">The API reports effective variant prices, not whether an override exists. “Keep current pricing” sends no price change. Stock can change after a response. No automatic write retries or cross-tab conflict protection are provided.</p>
  </>
}
function CategoryForm({ current, choices, disabled, save }: { current: CategoryChoice | null; choices: CategoryChoice[]; disabled: boolean; save: (id: string | null) => void }) {
  const [selected, setSelected] = useState(current?.id ?? '')
  const missing = current && !choices.some((row) => row.id === current.id)
  const valid = selected === '' || choices.some((row) => row.id === selected)
  return <form className="auth-form" onSubmit={(e) => { e.preventDefault(); if (!disabled && valid && selected !== (current?.id ?? '')) save(selected || null) }}>
    <div className="field"><label htmlFor="product-category">Product category</label><select id="product-category" disabled={disabled} value={selected} onChange={(e) => setSelected(e.target.value)}>
      <option value="">Uncategorized</option>{missing && <option value={current.id} disabled>{current.name} (not currently available)</option>}{choices.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
    </select></div>
    {missing && <p>The saved category is not currently selectable. It will be preserved unless you explicitly choose another category or Uncategorized.</p>}
    <Button type="submit" disabled={disabled || !valid || selected === (current?.id ?? '')}>Save category</Button>
  </form>
}
function VariantForm({ initial, disabled, save, cancel }: { initial?: Variant; disabled: boolean; save: (body: VariantPayload) => void; cancel: () => void }) {
  const [draft, setDraft] = useState<VariantDraft>({ size_type: initial?.size_type ?? 'alpha', size_value: initial?.size_value ?? '', colour: initial?.colour ?? '', stock: '0', priceMode: initial ? 'keep' : 'inherit', price: '', is_active: initial?.is_active ?? true })
  const [error, setError] = useState<unknown>(null)
  return <form className="account-card auth-form" onSubmit={(e) => { e.preventDefault(); if (disabled) return; try { const body = variantPayload(draft, initial); setError(null); save(body) } catch (reason) { setError(reason) } }}>
    <h3>{initial ? 'Edit variant' : 'New variant'}</h3>
    <div className="field"><label htmlFor="variant-size-type">Size type</label><select id="variant-size-type" disabled={disabled} value={draft.size_type} onChange={(e) => setDraft({ ...draft, size_type: e.target.value })}><option value="alpha">Alpha</option><option value="numeric">Numeric</option><option value="one_size">One size</option></select></div>
    <Field label="Size value" required maxLength={10} disabled={disabled} value={draft.size_value} onChange={(e) => setDraft({ ...draft, size_value: e.target.value })} />
    <Field label="Colour" required maxLength={50} disabled={disabled} value={draft.colour} onChange={(e) => setDraft({ ...draft, colour: e.target.value })} />
    {!initial && <Field label="Initial stock" required inputMode="numeric" disabled={disabled} value={draft.stock} onChange={(e) => setDraft({ ...draft, stock: e.target.value })} hint="A new SKU is generated by the server. Existing stock adjustments belong to inventory management." />}
    <div className="field"><label htmlFor="variant-pricing">Pricing action</label><select id="variant-pricing" disabled={disabled} value={draft.priceMode} onChange={(e) => setDraft({ ...draft, priceMode: e.target.value })}>{initial && <option value="keep">Keep current pricing</option>}<option value="inherit">Inherit product price</option><option value="set">Set price override</option></select></div>
    {draft.priceMode === 'set' && <Field label="Price override (PKR)" required inputMode="numeric" disabled={disabled} value={draft.price} onChange={(e) => setDraft({ ...draft, price: e.target.value })} hint="Whole PKR amount from 100 to 500,000." />}
    {initial && <label><input type="checkbox" checked={draft.is_active} disabled={disabled} onChange={(e) => setDraft({ ...draft, is_active: e.target.checked })} /> Variant active</label>}
    {Boolean(error) && <ErrorNotice error={error} />}
    <Button type="submit" disabled={disabled}>{initial ? 'Save variant' : 'Create variant'}</Button><Button className="button-secondary" disabled={disabled} onClick={cancel}>Cancel variant edits</Button>
  </form>
}
