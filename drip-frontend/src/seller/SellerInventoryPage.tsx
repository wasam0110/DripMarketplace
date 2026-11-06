import { useCallback, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { useOrderRead } from '../orders/api'
import { validateSellerSummary } from './SellerStatus'
import { confirmStock, inventoryMarker, stockCommand, validateInventory, validateStock, type AdjustmentReceipt, type InventoryPage, type StockCommand, type StockRow } from './inventory'

export function SellerInventoryPage() {
  const { user, loading, error } = useAuth()
  if (loading) return <section className="container page"><h1>Your inventory</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to manage inventory</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'seller') return <section className="container page"><h1>A seller account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page account-page"><Link className="text-link" to="/seller">Back to seller workspace</Link><p className="eyebrow">WearHowZ · Your label</p><h1>Your inventory</h1><InventoryAccess key={user.id} owner={user.id} /></section>
}
function InventoryAccess({ owner }: { owner: string }) {
  const resource = useOrderRead('/seller/me', true, validateSellerSummary)
  return <>{resource.loading && <p role="status">Checking seller access…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && (resource.data.status === 'active' ? <Inventory key={resource.data.id} owner={owner} /> : <p>An active seller account is required to manage inventory.</p>)}
    {!resource.data && <Button disabled={resource.loading} onClick={resource.retry}>Retry seller access</Button>}</>
}
function Inventory({ owner }: { owner: string }) {
  const [search, setSearch] = useState(''), [query, setQuery] = useState(''), [low, setLow] = useState(false), [page, setPage] = useState(1)
  const [selected, setSelected] = useState<StockRow | null>(null)
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(inventoryMarker(owner)) !== null } catch { return true } })
  const [savedNotice, setSavedNotice] = useState('')
  const write = useAccountWrite()
  const validate = useCallback((value: InventoryPage) => validateInventory(value, page, low), [page, low])
  const params = new URLSearchParams({ page: String(page), per_page: '20', low_stock_only: String(low) }); if (query) params.set('q', query)
  const resource = useOrderRead(`/seller/inventory?${params}`, true, validate)
  const locked = write.busy || write.blocked || pending
  function refresh() { setSelected(null); resource.retry() }
  function save(command: StockCommand, before: StockRow) {
    if (locked) return
    void write.run(async () => {
      sessionStorage.setItem(inventoryMarker(owner), 'pending'); setPending(true); setSavedNotice('')
      let response: StockRow | AdjustmentReceipt
      try {
        response = await request<StockRow | AdjustmentReceipt>(`/seller/inventory/${before.variant_id}${command.kind === 'adjust' ? '/adjust' : ''}`, { authenticated: true, method: command.kind === 'adjust' ? 'POST' : 'PUT', body: JSON.stringify(command.body) })
      } catch (reason) {
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(inventoryMarker(owner)); setPending(false) }
        throw reason
      }
      const message = confirmStock(response, command, before)
      sessionStorage.removeItem(inventoryMarker(owner)); setPending(false)
      return message
    }, (message) => { setSavedNotice(message); refresh() }, '')
  }
  return <>
    <p>Track physical units, quantities reserved for orders, and stock available to sell.</p>
    <form className="account-card auth-form" onSubmit={(e) => { e.preventDefault(); if (!write.busy) { setSelected(null); setPage(1); setQuery(search.trim()) } }}>
      <Field label="Search products or SKU" maxLength={100} value={search} disabled={write.busy} onChange={(e) => setSearch(e.target.value)} />
      <Button type="submit" disabled={write.busy}>Search inventory</Button>
      <label><input type="checkbox" checked={low} disabled={write.busy} onChange={(e) => { setSelected(null); setPage(1); setLow(e.target.checked) }} /> Low stock only</label>
    </form>
    <WriteFeedback state={write} />{savedNotice && <p role="status">{savedNotice}</p>}
    {pending && !write.busy && <p role="alert">A stock change is awaiting confirmation. Check the latest inventory and contact support to resolve it before making another change.</p>}
    {resource.loading && <p role="status">Loading inventory…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && <>
      <p>{resource.data.total} matching variants</p>
      {!resource.data.data.length && <EmptyState title="No inventory on this page"><p>Try another search or filter, or return to the previous page.</p></EmptyState>}
      {resource.data.data.map((row) => <article className="account-card" key={row.variant_id} style={{ overflowWrap: 'anywhere' }}>
        <h2>{row.product_name}</h2><p>{row.size ?? 'Size unavailable'} · {row.colour ?? 'Colour unavailable'} · SKU: {row.sku ?? 'Unavailable'}</p>
        <dl><dt>Physical stock</dt><dd>{row.stock}</dd><dt>Reserved for orders</dt><dd>{row.reserved}</dd><dt>Available to sell</dt><dd>{row.available}</dd><dt>Low-stock threshold</dt><dd>{row.reorder_point}</dd></dl>
        {row.is_low_stock && <p>Low stock</p>}
        <Button className="button-secondary" disabled={locked || resource.loading} onClick={() => setSelected(row)}>Manage stock {row.sku ?? row.variant_id}</Button>
      </article>)}
      <p>Page {page}{resource.data.pages ? ` of ${resource.data.pages}` : ''}</p>
    </>}
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
      <Button className="button-secondary" disabled={write.busy || resource.loading || page === 1} onClick={() => { setSelected(null); setPage(page - 1) }}>Previous page</Button>
      <Button className="button-secondary" disabled={write.busy || resource.loading || !resource.data || page >= resource.data.pages} onClick={() => { setSelected(null); setPage(page + 1) }}>Next page</Button>
      <Button className="button-secondary" disabled={write.busy || resource.loading} onClick={refresh}>Refresh inventory</Button>
    </div>
    {selected && <StockEditor key={selected.variant_id} selected={selected} disabled={locked} save={save} cancel={() => setSelected(null)} />}
    <p className="muted">Quantities can change as orders are placed or fulfilled. Refresh for the latest figures.</p>
  </>
}
function StockEditor({ selected, disabled, save, cancel }: { selected: StockRow; disabled: boolean; save: (command: StockCommand, before: StockRow) => void; cancel: () => void }) {
  const validate = useCallback((value: StockRow) => validateStock(value, selected.variant_id, selected.product_id), [selected.variant_id, selected.product_id])
  const resource = useOrderRead(`/seller/inventory/${selected.variant_id}`, true, validate)
  return <section aria-label="Manage variant stock">
    <h2>Manage stock: {selected.sku ?? selected.product_name}</h2>
    {resource.loading && <p role="status">Loading latest stock…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && <StockForm key={JSON.stringify(resource.data)} snapshot={resource.data} disabled={disabled} save={save} />}
    <Button className="button-secondary" disabled={disabled || resource.loading} onClick={resource.retry}>Refresh stock details and discard edits</Button>
    <Button className="button-secondary" disabled={disabled} onClick={cancel}>Close stock editor</Button>
  </section>
}
function StockForm({ snapshot, disabled, save }: { snapshot: StockRow; disabled: boolean; save: (command: StockCommand, before: StockRow) => void }) {
  const [mode, setMode] = useState<'adjust' | 'set'>('adjust'), [quantity, setQuantity] = useState(''), [reason, setReason] = useState(''), [reorder, setReorder] = useState(String(snapshot.reorder_point))
  const [command, setCommand] = useState<StockCommand | null>(null), [error, setError] = useState<unknown>(null)
  return <div className="account-card">
    <p>Latest physical stock: {snapshot.stock}. Reserved: {snapshot.reserved}. Available: {snapshot.available}.</p>
    <form className="auth-form" onSubmit={(e) => { e.preventDefault(); if (disabled) return; try { setCommand(stockCommand(mode, quantity, reason, reorder, snapshot)); setError(null) } catch (value) { setError(value) } }}>
      <div className="field"><label htmlFor="stock-action">Stock action</label><select id="stock-action" value={mode} disabled={disabled || !!command} onChange={(e) => { setMode(e.target.value as 'adjust' | 'set'); setQuantity(''); setError(null) }}><option value="adjust">Add or remove units</option><option value="set">Set a physical stock count</option></select></div>
      <Field label={mode === 'adjust' ? 'Quantity change' : 'Total physical stock'} required inputMode={mode === 'adjust' ? 'text' : 'numeric'} value={quantity} disabled={disabled || !!command} onChange={(e) => setQuantity(e.target.value)} hint={mode === 'adjust' ? 'Use a positive number to add units or a negative number to remove them. Maximum 10,000 units per change.' : 'Enter the total units physically held, including units reserved for orders.'} />
      {mode === 'adjust' ? <Field label="Adjustment reason" required minLength={3} maxLength={200} value={reason} disabled={disabled || !!command} onChange={(e) => setReason(e.target.value)} /> : <Field label="Low-stock threshold" required inputMode="numeric" value={reorder} disabled={disabled || !!command} onChange={(e) => setReorder(e.target.value)} />}
      {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || !!command}>Review stock change</Button>
    </form>
    {command && <div aria-label="Review stock change">
      <h3>Review stock change</h3><p>{command.kind === 'adjust' ? `${command.body.delta > 0 ? 'Add' : 'Remove'} ${Math.abs(command.body.delta)} units. Reason: ${command.body.reason}` : `Set total physical stock to ${command.body.stock} units. Low-stock threshold: ${command.body.reorder_point ?? snapshot.reorder_point}.`}</p>
      <p>{command.kind === 'adjust' ? 'This change applies to the quantity held when the server processes it.' : 'This replaces the current physical stock count. Check your count carefully before confirming.'} Reserved units remain protected.</p>
      <Button disabled={disabled} onClick={() => save(command, snapshot)}>Confirm stock change</Button><Button className="button-secondary" disabled={disabled} onClick={() => setCommand(null)}>Back to stock edits</Button>
    </div>}
  </div>
}
