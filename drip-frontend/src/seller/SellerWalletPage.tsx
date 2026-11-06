import { useCallback, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, request } from '../api/client'
import { formatPrice } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, EmptyState, ErrorNotice, Field } from '../components/ui'
import { useAccountWrite, WriteFeedback } from '../account/AccountDetails'
import { orderDate, useOrderRead } from '../orders/api'
import { validateSellerSummary } from './SellerStatus'
import { bankPayload, confirmBank, confirmWithdrawal, maskAccount, payoutLabel, payoutStatuses, transactionTypes, usableBank, validateBanks, validatePayout, validateTransaction, validateWallet, validateWalletPage, walletMarker, withdrawalBody, type BankAccount, type BankDraft, type BankPayload, type Payout, type WalletPage, type WalletSummary, type WalletTransaction, type Withdrawal } from './wallet'

export function SellerWalletPage({ accountsOnly = false }: { accountsOnly?: boolean }) {
  const { user, loading, error } = useAuth()
  if (loading) return <section className="container page"><h1>Your wallet</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to manage your wallet</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'seller') return <section className="container page"><h1>A seller account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page account-page" style={{ overflowWrap: 'anywhere' }}><Link className="text-link" to="/seller">Back to seller workspace</Link><p className="eyebrow">WearHowZ · Your label</p><h1>{accountsOnly ? 'Payout bank accounts' : 'Your wallet'}</h1><WalletAccess key={`${user.id}:${accountsOnly}`} owner={user.id} accountsOnly={accountsOnly} /></section>
}
function WalletAccess({ owner, accountsOnly }: { owner: string; accountsOnly: boolean }) {
  const resource = useOrderRead('/seller/me', true, validateSellerSummary)
  return <>{resource.loading && <p role="status">Checking seller access…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && (resource.data.status === 'active' ? <WalletManager key={resource.data.id} owner={owner} accountsOnly={accountsOnly} /> : <p>An active seller account is required to manage your wallet.</p>)}
    {!resource.data && <Button disabled={resource.loading} onClick={resource.retry}>Retry seller access</Button>}</>
}
function WalletManager({ owner, accountsOnly }: { owner: string; accountsOnly: boolean }) {
  const wallet = useOrderRead('/seller/wallet', true, validateWallet), accounts = useOrderRead('/seller/bank-accounts', true, validateBanks)
  const write = useAccountWrite()
  const [pending, setPending] = useState(() => { try { return sessionStorage.getItem(walletMarker(owner)) !== null } catch { return true } })
  const [view, setView] = useState<'overview' | 'transactions' | 'payouts'>('overview')
  const [adding, setAdding] = useState(false), [removing, setRemoving] = useState<BankAccount | null>(null), [receipt, setReceipt] = useState<Payout | null>(null)
  const locked = write.busy || write.blocked || pending
  function refresh() { setAdding(false); setRemoving(null); wallet.retry(); accounts.retry() }
  function run<T>(operation: (sending: () => void) => Promise<T>, confirmed: (value: T) => void, message: string) {
    if (locked) return
    void write.run(async () => {
      let sent = false
      const sending = () => { sessionStorage.setItem(walletMarker(owner), 'pending'); sent = true; setPending(true) }
      try {
        const result = await operation(sending)
        sessionStorage.removeItem(walletMarker(owner)); setPending(false)
        return result
      } catch (reason) {
        if (!sent) throw new ApiError(reason instanceof Error ? reason.message : 'Refresh wallet data before trying again.', 409)
        if (reason instanceof ApiError && [400, 401, 403, 404, 409, 422, 429].includes(reason.status)) { sessionStorage.removeItem(walletMarker(owner)); setPending(false) }
        throw reason
      }
    }, confirmed, message)
  }
  async function bankReadBack(check: (rows: BankAccount[]) => boolean) {
    try { const rows = validateBanks(await request<BankAccount[]>('/seller/bank-accounts', { authenticated: true, cache: 'no-store' })); if (!check(rows)) throw new Error('Mismatch') }
    catch { throw new Error('The bank account change could not be confirmed. Inspect your accounts before repeating it.') }
  }
  function withdraw(body: Withdrawal, destination: BankAccount, reviewed: WalletSummary) {
    run(async (sending) => {
      const [latestWallet, latestAccounts] = await Promise.all([
        request<WalletSummary>('/seller/wallet', { authenticated: true, cache: 'no-store' }).then(validateWallet),
        request<BankAccount[]>('/seller/bank-accounts', { authenticated: true, cache: 'no-store' }).then(validateBanks),
      ])
      const latest = latestAccounts.find((row) => row.id === destination.id)
      try {
        withdrawalBody(body.amount, body.bank_account_id, body.note ?? '', latestWallet, latestAccounts)
        if (!latest || latest.bank_name !== destination.bank_name || latest.account_number !== destination.account_number || latest.account_title !== destination.account_title
          || latestWallet.minimum_withdrawal_amount !== reviewed.minimum_withdrawal_amount || latestWallet.maximum_withdrawal_amount !== reviewed.maximum_withdrawal_amount) throw new Error('Payout limits or bank details changed. Review the refreshed details before requesting a payout.')
      } catch (reason) { refresh(); throw reason }
      sending()
      const saved = confirmWithdrawal(await request<Payout>('/seller/wallet/withdraw', { authenticated: true, method: 'POST', body: JSON.stringify(body) }), body, destination)
      return saved
    }, (saved) => { setReceipt(saved); refresh() }, 'Payout request recorded. Admin will process the transfer.')
  }
  return <>
    <p><Link className="text-link" to={accountsOnly ? '/seller/wallet' : '/seller/wallet/accounts'}>{accountsOnly ? 'Back to wallet' : 'Manage payout bank accounts'}</Link></p>
    <WriteFeedback state={write} />
    {pending && !write.busy && <p role="alert">A wallet or bank-account change is awaiting confirmation. Inspect your records or contact support before making another change.</p>}
    {receipt && <section className="account-card"><h2>New payout request</h2><p>Reference: {receipt.id}</p><p>{formatPrice(receipt.amount)} · {payoutLabel(receipt.status)}</p></section>}
    {wallet.loading && <p role="status">Loading wallet…</p>}{Boolean(wallet.error) && <ErrorNotice error={wallet.error} />}
    {!accountsOnly && wallet.data && <section className="account-card"><h2>Your balances</h2><dl>
      <dt>Available to request</dt><dd>{formatPrice(wallet.data.available_balance)}</dd><dt>Pending release</dt><dd>{formatPrice(wallet.data.pending_balance)}</dd>
      <dt>Recorded earnings</dt><dd>{formatPrice(wallet.data.total_earned)}</dd><dt>Recorded commission</dt><dd>{formatPrice(wallet.data.total_commission)}</dd>
    </dl><p>Pending earnings must be released before they can be withdrawn. Payout requests reserve funds from your available balance.</p><p>Current payout range: {formatPrice(wallet.data.minimum_withdrawal_amount)}–{formatPrice(wallet.data.maximum_withdrawal_amount)}.</p></section>}
    {accounts.loading && <p role="status">Loading payout accounts…</p>}{Boolean(accounts.error) && <ErrorNotice error={accounts.error} />}
    {accountsOnly ? <>
      {accounts.data && <>
        {!accounts.data.length && <EmptyState title="No payout accounts saved"><p>Add your bank details to request payouts.</p></EmptyState>}
        {accounts.data.map((row) => <article className="account-card" key={row.id}><h2>{row.bank_name || 'Bank name unavailable'}</h2><p>{row.account_title || 'Account title not supplied'} · {maskAccount(row.account_number)}{row.is_default ? ' · Default' : ''}</p><Button className="button-secondary" disabled={locked} onClick={() => setRemoving(row)}>Remove account {maskAccount(row.account_number)}</Button></article>)}
        <Button disabled={locked || accounts.loading} onClick={() => { setRemoving(null); setAdding(true) }}>Add bank account</Button>
      </>}
      {adding && <BankForm disabled={locked} cancel={() => setAdding(false)} save={(body) => run(async (sending) => {
        sending()
        const saved = confirmBank(await request<BankAccount>('/seller/bank-accounts', { authenticated: true, method: 'POST', body: JSON.stringify(body) }), body)
        await bankReadBack((rows) => rows.some((row) => row.id === saved.id && row.bank_name === body.bank_name && row.account_number === body.account_number && row.account_title === body.account_title && row.is_default === body.is_default))
        return saved
      }, refresh, 'Payout bank account saved and confirmed.')} />}
      {removing && <section className="account-card"><h2>Remove payout account?</h2><p>{removing.bank_name} · {maskAccount(removing.account_number)}</p><p>Existing payout requests keep their recorded transfer details. Removing this account prevents selecting it for a new request.</p><Button disabled={locked} onClick={() => run(async (sending) => {
        sending(); await request(`/seller/bank-accounts/${removing.id}`, { authenticated: true, method: 'DELETE' }); await bankReadBack((rows) => !rows.some((row) => row.id === removing.id))
      }, refresh, 'Payout bank account removal confirmed.')}>Confirm account removal</Button><Button className="button-secondary" disabled={write.busy} onClick={() => setRemoving(null)}>Cancel account removal</Button></section>}
    </> : <>
      <div aria-label="Wallet view" style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>{(['overview', 'transactions', 'payouts'] as const).map((tab) => <Button className="button-secondary" key={tab} aria-pressed={view === tab} disabled={write.busy} onClick={() => setView(tab)}>{tab === 'overview' ? 'Request payout' : tab === 'transactions' ? 'Transactions' : 'Payout history'}</Button>)}</div>
      {view === 'overview' && wallet.data && accounts.data && <WithdrawalForm key={JSON.stringify([wallet.data, accounts.data])} wallet={wallet.data} accounts={accounts.data} disabled={locked || wallet.loading || accounts.loading} save={(body, account) => withdraw(body, account, wallet.data!)} />}
      {view === 'transactions' && <TransactionHistory />}{view === 'payouts' && <PayoutHistory />}
    </>}
    <Button className="button-secondary" disabled={write.busy || wallet.loading || accounts.loading} onClick={refresh}>Refresh wallet and accounts</Button>
  </>
}
function WithdrawalForm({ wallet, accounts, disabled, save }: { wallet: WalletSummary; accounts: BankAccount[]; disabled: boolean; save: (body: Withdrawal, account: BankAccount) => void }) {
  const [amount, setAmount] = useState(''), [bank, setBank] = useState(''), [note, setNote] = useState(''), [review, setReview] = useState<Withdrawal | null>(null), [error, setError] = useState<unknown>(null)
  const validAccounts = accounts.filter(usableBank), selected = validAccounts.find((row) => row.id === bank)
  if (!validAccounts.length) return <p>Add a bank payout account before requesting a withdrawal.</p>
  return <section className="account-card"><h2>Request a payout</h2><form className="auth-form" onSubmit={(e) => { e.preventDefault(); if (disabled) return; try { setReview(withdrawalBody(amount, bank, note, wallet, accounts)); setError(null) } catch (reason) { setError(reason) } }}>
    <Field label="Payout amount (PKR)" required inputMode="decimal" value={amount} disabled={disabled || !!review} onChange={(e) => setAmount(e.target.value)} />
    <div className="field"><label htmlFor="payout-destination">Payout bank account</label><select id="payout-destination" required value={bank} disabled={disabled || !!review} onChange={(e) => setBank(e.target.value)}><option value="">Choose an account</option>{validAccounts.map((row) => <option key={row.id} value={row.id}>{row.bank_name} · {row.account_title || 'Account'} · {maskAccount(row.account_number)}</option>)}</select></div>
    <Field label="Payout note (optional)" maxLength={300} value={note} disabled={disabled || !!review} onChange={(e) => setNote(e.target.value)} />
    {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || !!review}>Review payout request</Button>
  </form>{review && selected && <div aria-label="Review payout request"><h3>Review payout request</h3><p>{formatPrice(review.amount)} to {selected.bank_name} · {selected.account_title || 'Account title not supplied'} · {maskAccount(selected.account_number)}.</p><p>The amount will be reserved from your available balance. Admin reviews and processes the transfer.</p><Button disabled={disabled} onClick={() => save(review, selected)}>Confirm payout request</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to payout edits</Button></div>}</section>
}
function BankForm({ disabled, save, cancel }: { disabled: boolean; save: (body: BankPayload) => void; cancel: () => void }) {
  const [draft, setDraft] = useState<BankDraft>({ bank_name: '', account_title: '', account_number: '', is_default: false }), [review, setReview] = useState<BankPayload | null>(null), [error, setError] = useState<unknown>(null)
  return <section className="account-card"><h2>Add bank account</h2><form className="auth-form" onSubmit={(e) => { e.preventDefault(); if (disabled) return; try { setReview(bankPayload(draft)); setError(null) } catch (reason) { setError(reason) } }}>
    {(['bank_name', 'account_title', 'account_number'] as const).map((field) => <Field key={field} label={field === 'bank_name' ? 'Bank name' : field === 'account_title' ? 'Account title (optional)' : 'Bank account number'} autoComplete="off" required={field !== 'account_title'} maxLength={field === 'bank_name' ? 100 : field === 'account_title' ? 200 : 50} value={draft[field]} disabled={disabled || !!review} onChange={(e) => setDraft({ ...draft, [field]: e.target.value })} />)}
    <label><input type="checkbox" checked={draft.is_default} disabled={disabled || !!review} onChange={(e) => setDraft({ ...draft, is_default: e.target.checked })} /> Save as default account</label>
    {Boolean(error) && <ErrorNotice error={error} />}<Button type="submit" disabled={disabled || !!review}>Review bank account</Button>
  </form>{review && <div aria-label="Review bank account"><h3>Check your bank details</h3><p>{review.bank_name} · {review.account_title || 'Account title not supplied'}</p><p>Account number: {review.account_number}</p><p>Confirm these details are correct before saving.</p><Button disabled={disabled} onClick={() => save(review)}>Confirm bank account</Button><Button className="button-secondary" disabled={disabled} onClick={() => setReview(null)}>Back to bank edits</Button></div>}<Button className="button-secondary" disabled={disabled} onClick={cancel}>Cancel bank account</Button></section>
}
function TransactionHistory() {
  const [page, setPage] = useState(1), [filter, setFilter] = useState('')
  const validate = useCallback((value: WalletPage<WalletTransaction>) => { validateWalletPage(value, page, validateTransaction); if (value.per_page !== 25 || (filter && value.data.some((row) => row.type !== filter))) throw new Error('Transaction history could not be verified.'); return value }, [page, filter])
  const resource = useOrderRead(`/seller/wallet/transactions?page=${page}&per_page=25${filter ? `&tx_type=${filter}` : ''}`, true, validate)
  return <section><h2>Wallet transactions</h2><div className="field"><label htmlFor="wallet-tx-filter">Transaction type</label><select id="wallet-tx-filter" value={filter} onChange={(e) => { setFilter(e.target.value); setPage(1) }}><option value="">All transactions</option>{transactionTypes.map((type) => <option key={type} value={type}>{transactionLabel(type)}</option>)}</select></div>
    {resource.loading && <p role="status">Loading transactions…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && <>{!resource.data.data.length && <p>No transactions on this page.</p>}{resource.data.data.map((row) => <article className="account-card" key={row.id}><h3>{transactionLabel(row.type)}</h3><p>{formatPrice(row.amount)} · {orderDate(row.created_at)}</p><p>Recorded balance after: {formatPrice(row.balance_after)}</p>{row.reference && <p>Reference: {row.reference}</p>}{row.note && <p>{row.note}</p>}</article>)}<p>Page {page} of {resource.data.total_pages}</p></>}
    <HistoryButtons page={page} pages={resource.data?.total_pages} loading={resource.loading} setPage={setPage} refresh={resource.retry} />
  </section>
}
function PayoutHistory() {
  const [page, setPage] = useState(1), [filter, setFilter] = useState('')
  const validate = useCallback((value: WalletPage<Payout>) => { validateWalletPage(value, page, validatePayout); if (filter && value.data.some((row) => row.status !== filter)) throw new Error('Payout history could not be verified.'); return value }, [page, filter])
  const resource = useOrderRead(`/seller/wallet/payouts?page=${page}${filter ? `&status=${filter}` : ''}`, true, validate)
  return <section><h2>Payout history</h2><div className="field"><label htmlFor="wallet-payout-filter">Payout status</label><select id="wallet-payout-filter" value={filter} onChange={(e) => { setFilter(e.target.value); setPage(1) }}><option value="">All payouts</option>{payoutStatuses.map((status) => <option key={status} value={status}>{payoutLabel(status)}</option>)}</select></div>
    {resource.loading && <p role="status">Loading payouts…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}
    {resource.data && <>{!resource.data.data.length && <p>No payouts on this page.</p>}{resource.data.data.map((row) => <article className="account-card" key={row.id}><h3>{payoutLabel(row.status)}</h3><p>{formatPrice(row.amount)} · Requested {orderDate(row.requested_at)}</p><p>Reference: {row.id}</p><PayoutDestination value={row.payment_detail} />{row.admin_note && <p>Admin note: {row.admin_note}</p>}{row.completed_at && <p>Transfer recorded {orderDate(row.completed_at)}</p>}{row.transfer_reference && <p>Transfer reference: {row.transfer_reference}</p>}{row.status === 'completed' && !row.transfer_reference && <p>Transfer reference not recorded.</p>}</article>)}<p>Page {page} of {resource.data.total_pages}</p></>}
    <p className="muted">Statuses and references reflect platform records. Check your bank statement to confirm receipt.</p><HistoryButtons page={page} pages={resource.data?.total_pages} loading={resource.loading} setPage={setPage} refresh={resource.retry} />
  </section>
}
function PayoutDestination({ value }: { value: string }) { const [show, setShow] = useState(false); return <><p>Transfer destination: {show ? value : 'Hidden'}</p><Button className="button-secondary" onClick={() => setShow(!show)}>{show ? 'Hide transfer destination' : 'Show transfer destination'}</Button></> }
function HistoryButtons({ page, pages, loading, setPage, refresh }: { page: number; pages?: number; loading: boolean; setPage: (page: number) => void; refresh: () => void }) { return <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}><Button className="button-secondary" disabled={loading || page === 1} onClick={() => setPage(page - 1)}>Previous page</Button><Button className="button-secondary" disabled={loading || !pages || page >= pages} onClick={() => setPage(page + 1)}>Next page</Button><Button className="button-secondary" disabled={loading} onClick={refresh}>Refresh history</Button></div> }
function transactionLabel(type: string) { switch (type) { case 'credit_commission': return 'Earnings credited'; case 'debit_commission': return 'Commission debited'; case 'credit_refund': return 'Funds returned'; case 'debit_withdrawal': return 'Withdrawal reserved'; case 'credit_adjustment': return 'Credit adjustment'; case 'debit_adjustment': return 'Debit adjustment'; default: return 'Transaction type unavailable' } }
