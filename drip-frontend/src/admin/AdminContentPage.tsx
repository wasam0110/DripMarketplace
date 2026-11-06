import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, request } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { validateAvatarDimensions } from '../account/avatar'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { isOrderId, orderDate, useOrderRead } from '../orders/api'
import { moderationImage } from './products'
import { bannerDraft, bannerMarker, bannerPayload, bannerPositions, confirmBanner, sameBanner, validateBannerFile, validateBanners, type AdminBanner, type BannerDraft } from './content'
import './products.css'

const path = '/admin/content/banners'
export function AdminContentPage({ detail = false, create = false }: { detail?: boolean; create?: boolean }) {
  const { user, loading, error } = useAuth(), { id = '' } = useParams()
  if (loading) return <section className="container page"><h1>Banner management</h1><p role="status">Checking your session...</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to manage banners</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page admin-products"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Storefront content</p><h1>{create ? 'Create banner' : detail ? 'Manage banner' : 'Banner management'}</h1>
    {detail && !isOrderId(id) ? <p role="alert">This banner reference is invalid.</p> : <BannerManager key={`${user.id}:${create ? 'new' : detail ? id : 'list'}`} owner={user.id} id={detail ? id : undefined} create={create} />}
  </section>
}
function BannerManager({ owner, id, create }: { owner: string; id?: string; create: boolean }) {
  const resource = useOrderRead(path, true, validateBanners), write = useAccountWrite(), active = useRef(false)
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  const key = bannerMarker(owner, create ? 'new' : id ?? 'list')
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(key) !== null } catch { return true } })
  const [deleting, setDeleting] = useState<AdminBanner | null>(null), [created, setCreated] = useState<string | null>(null)
  const disabled = write.busy || write.blocked || pending || resource.loading || !!created
  const row = resource.data?.find((item) => item.id === id)
  function refresh() { setDeleting(null); resource.retry() }
  function save(kind: 'create' | 'update' | 'delete', before?: AdminBanner, payload?: ReturnType<typeof bannerPayload>, file?: File) {
    if (disabled) return
    void write.run(async () => {
      let sent = false, saved: AdminBanner | undefined
      try {
        const latest = validateBanners(await request<AdminBanner[]>(path, { authenticated: true, cache: 'no-store' }))
        if (!active.current) throw new Error('The admin session changed. No change was sent.')
        if (before && !latest.some((item) => item.id === before.id && sameBanner(before, item))) { refresh(); throw new Error('The banner changed or was removed. Review the refreshed list before deciding.') }
        sessionStorage.setItem(key, 'pending'); setPending(true); sent = true
        if (kind === 'delete' && before) {
          const receipt = await request<void>(`${path}/${before.id}?${new URLSearchParams({ expected_updated_at: before.updated_at })}`, { authenticated: true, method: 'DELETE' })
          if (receipt !== undefined) throw new Error('The banner deletion receipt could not be verified.')
        } else if (payload) {
          if (kind === 'create' && file) {
            const body = new FormData(); for (const field of ['title', 'link_url', 'position', 'sort_order', 'is_active'] as const) { if (payload[field] !== null) body.append(field, String(payload[field])) }; body.append('image', file)
            saved = confirmBanner(await request<AdminBanner>(path, { authenticated: true, method: 'POST', body }), payload)
            if (latest.some((item) => item.id === saved!.id)) throw new Error('The created banner reference was already present. Inspect the list before repeating.')
          } else if (before) saved = confirmBanner(await request<AdminBanner>(`${path}/${before.id}`, { authenticated: true, method: 'PATCH', body: JSON.stringify({ ...payload, expected_updated_at: before.updated_at }) }), payload, before)
        }
      } catch (reason) {
        if (!sent) throw new ApiError(reason instanceof Error ? reason.message : 'The banner list could not be rechecked. No change was sent.', 409)
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 413, 415, 422, 429].includes(reason.status)) { sessionStorage.removeItem(key); setPending(false) }
        throw reason
      }
      try {
        const latest = validateBanners(await request<AdminBanner[]>(path, { authenticated: true, cache: 'no-store' }))
        if (kind === 'delete') { if (latest.some((item) => item.id === before?.id)) throw new Error() }
        else {
          const found = latest.find((item) => item.id === saved?.id)
          if (!found || !payload || !saved || found.image_url !== saved.image_url) throw new Error()
          confirmBanner(found, payload, before)
        }
      } catch { throw new Error('The saved banner change could not be confirmed. Inspect the list before repeating it.') }
      sessionStorage.removeItem(key); setPending(false); return saved
    }, (saved) => { if (kind === 'create' && saved) setCreated(saved.id); refresh() }, kind === 'delete' ? 'Banner record deleted and confirmed.' : 'Banner saved and confirmed.')
  }
  return <>{(id || create) && <p><Link className="text-link" to="/admin/content">Back to banner management</Link></p>}<p>Manage saved banner placements, display order and UTC schedules. Active and schedule flags do not prove a placement is currently rendered by the storefront.</p>
    {resource.loading && <p role="status">Loading banners...</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}<WriteFeedback state={write} />
    {pending && !write.busy && <p role="alert">A banner change is awaiting confirmation. Inspect the saved list or contact support before another change.</p>}
    {created && <p><Link className="text-link" to={`/admin/content/banners/${created}`}>Open the created banner</Link></p>}
    {resource.data && (create ? !created && <BannerForm key="new" disabled={disabled} save={(payload, file) => save('create', undefined, payload, file)} /> : id ? row ? <>
      <BannerCard row={row} /><BannerForm key={`${row.id}:${row.updated_at}`} initial={row} disabled={disabled || !!deleting} save={(payload) => save('update', row, payload)} />
      <section className="account-card"><h2>Remove banner record</h2><p>Deletion cannot be undone here. It removes this banner record, not its stored image or any products. Deactivate instead when you only want to stop its availability.</p><Button className="button-secondary" disabled={disabled || !!deleting} onClick={() => setDeleting(row)}>Review deleting banner</Button>
        {deleting && <div className="admin-product-confirm"><h3>Delete {deleting.title}?</h3><p>Banner reference: {deleting.id}</p><div className="option-row"><Button disabled={disabled} onClick={() => save('delete', deleting)}>Confirm banner deletion</Button><Button className="button-secondary" disabled={disabled} onClick={() => setDeleting(null)}>Keep banner</Button></div></div>}
      </section>
    </> : <p role="status">This banner is no longer in the saved list.</p> : <><p><Link className="text-link" to="/admin/content/banners/new">Create a banner</Link></p><p>{resource.data.length} saved banners · Lower sort orders appear first.</p>{!resource.data.length && <EmptyState title="No banners yet"><p>Create a banner when approved artwork is ready.</p></EmptyState>}{resource.data.map((item) => <BannerCard key={item.id} row={item} link />)}</>)}
    <Button className="button-secondary" disabled={write.busy || resource.loading} onClick={refresh}>Refresh banners and discard review</Button>
  </>
}
function BannerCard({ row, link = false }: { row: AdminBanner; link?: boolean }) {
  return <section className="account-card"><h2>{row.title}</h2><div className="admin-product-images">{moderationImage(row.image_url) ? <img src={moderationImage(row.image_url)!} alt={row.title} loading="lazy" referrerPolicy="no-referrer" /> : <p>Image URL unavailable.</p>}</div><dl><dt>Placement</dt><dd>{bannerPositions[row.position]}</dd><dt>Availability flag</dt><dd>{row.is_active ? 'Active' : 'Inactive'}</dd><dt>Sort order</dt><dd>{row.sort_order}</dd><dt>Starts (UTC)</dt><dd>{row.valid_from ?? 'No start limit'}</dd><dt>Ends (UTC)</dt><dd>{row.valid_until ?? 'No end limit'}</dd><dt>Destination</dt><dd>{row.link_url || 'No link'}</dd><dt>Last updated</dt><dd>{orderDate(row.updated_at)}</dd></dl>{link && <Link className="text-link" to={`/admin/content/banners/${row.id}`}>Manage {row.title}</Link>}</section>
}
function BannerForm({ initial, disabled, save }: { initial?: AdminBanner; disabled: boolean; save: (payload: ReturnType<typeof bannerPayload>, file?: File) => void }) {
  const [draft, setDraft] = useState(() => bannerDraft(initial)), [file, setFile] = useState<File | undefined>(), [preview, setPreview] = useState<string | null>(null), [checking, setChecking] = useState(false)
  const [review, setReview] = useState<ReturnType<typeof bannerPayload> | null>(null), [error, setError] = useState<unknown>(null), ticket = useRef(0)
  useEffect(() => () => { ticket.current++ }, [])
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])
  const locked = disabled || !!review || checking
  function change(key: keyof BannerDraft, value: string | boolean) { setDraft((current) => ({ ...current, [key]: value })) }
  async function choose(candidate?: File) {
    if (locked) return
    const current = ++ticket.current; setFile(undefined); setPreview(null); setError(null)
    if (!candidate) return
    setChecking(true)
    try { validateBannerFile(candidate); const bitmap = await createImageBitmap(candidate); try { validateAvatarDimensions(bitmap.width, bitmap.height) } finally { bitmap.close() }; if (current === ticket.current) { setFile(candidate); setPreview(URL.createObjectURL(candidate)) } }
    catch (reason) { if (current === ticket.current) setError(reason instanceof Error ? reason : new Error('The selected image could not be decoded.')) }
    finally { if (current === ticket.current) setChecking(false) }
  }
  return <form className="account-card auth-form" onSubmit={(event) => { event.preventDefault(); if (locked) return; try { if (!initial && !file) throw new Error('Choose and check an image first.'); setReview(bannerPayload(draft, initial)); setError(null) } catch (reason) { setError(reason) } }}>
    <h2>{initial ? 'Edit banner metadata' : 'New banner'}</h2><Field label="Banner title" value={draft.title} maxLength={200} disabled={locked} onChange={(event) => change('title', event.target.value)} />
    <div className="field"><label htmlFor="banner-position">Placement</label><select id="banner-position" value={draft.position} disabled={locked} onChange={(event) => change('position', event.target.value)}>{Object.entries(bannerPositions).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></div>
    <Field label="Destination link (optional)" value={draft.link} maxLength={500} disabled={locked} hint="Use a site-relative path beginning / or a credential-free HTTPS link. Leave blank for no link." onChange={(event) => change('link', event.target.value)} />
    <Field label="Sort order" inputMode="numeric" value={draft.order} maxLength={10} disabled={locked} onChange={(event) => change('order', event.target.value)} />
    <label><input type="checkbox" checked={draft.active} disabled={locked} onChange={(event) => change('active', event.target.checked)} /> Banner is active</label>
    {initial ? <><Field label="Starts (UTC, optional)" type="datetime-local" value={draft.start} disabled={locked} onChange={(event) => change('start', event.target.value)} /><Field label="Ends (UTC, optional)" type="datetime-local" value={draft.end} disabled={locked} onChange={(event) => change('end', event.target.value)} /><p>Times are UTC, not your device timezone. Blank fields remove the corresponding schedule limit. Image replacement is not supported by this update API.</p></> : <><p>New banners start inactive unless you choose otherwise. Upload approved JPEG, PNG or WebP artwork up to 5 MiB / 25 megapixels. The server converts it to WebP and may resize it. Add a schedule after creating the banner.</p><Field label="Banner image" type="file" accept="image/jpeg,image/png,image/webp" disabled={locked} onChange={(event) => { const candidate = event.target.files?.[0]; event.target.value = ''; void choose(candidate) }} />{checking && <p role="status">Checking banner image...</p>}{preview && <div className="admin-product-images"><img src={preview} alt="Selected banner preview, not yet uploaded" /></div>}</>}
    {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={locked || (!initial && !file)}>Review banner changes</Button>
    {review && <div className="admin-product-confirm"><h3>Confirm {initial ? 'banner update' : 'new banner'}</h3><dl><dt>Title</dt><dd>{review.title}</dd><dt>Placement</dt><dd>{bannerPositions[review.position]}</dd><dt>Active</dt><dd>{review.is_active ? 'Yes' : 'No'}</dd><dt>Sort order</dt><dd>{review.sort_order}</dd><dt>Destination</dt><dd>{review.link_url || 'No link'}</dd><dt>Starts (UTC)</dt><dd>{review.valid_from || 'No start limit'}</dd><dt>Ends (UTC)</dt><dd>{review.valid_until || 'No end limit'}</dd></dl><div className="option-row"><Button disabled={disabled} onClick={() => save(review, file)}>Confirm banner changes</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to banner form</Button></div></div>}
  </form>
}
