import { useCallback, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, EmptyState, ErrorNotice } from '../components/ui'
import { orderDate, useOrderRead } from '../orders/api'
import { validateSellerSummary } from './SellerStatus'
import { analyticsMoney, periods, validateCommission, validateInventoryHealth, validateOverview, validateRevenue, validateTopProducts, type CommissionEntry, type CommissionPage, type Granularity, type Overview, type Period, type Ranking, type RevenueSeries, type TopProducts } from './analytics'
import './analytics.css'

export function SellerAnalyticsPage() {
  const { user, loading, error } = useAuth()
  if (loading) return <section className="container page"><h1>Seller analytics</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to view seller analytics</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'seller') return <section className="container page"><h1>A seller account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page seller-analytics"><Link className="text-link" to="/seller">Back to seller workspace</Link><p className="eyebrow">WearHowZ · Your label</p><h1>Seller analytics</h1><AnalyticsAccess key={user.id} /></section>
}
function AnalyticsAccess() {
  const resource = useOrderRead('/seller/me', true, validateSellerSummary)
  return <ReadState resource={resource} label="seller access">
    {resource.data && (resource.data.status === 'active' ? <AnalyticsWorkspace key={resource.data.id} /> : <p>An active seller account is required to view analytics.</p>)}
  </ReadState>
}
function ReadState({ resource, label, children }: { resource: { loading: boolean; error: unknown; retry: () => void }; label: string; children: ReactNode }) {
  return <div aria-busy={resource.loading}>{resource.loading && <p role="status">Loading {label}…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}{children}<Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh {label}</Button></div>
}
function Metrics({ rows }: { rows: [string, string | number][] }) {
  return <dl className="analytics-metrics">{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
}
function AnalyticsWorkspace() {
  const [tab, setTab] = useState<'performance' | 'commission'>('performance')
  const [period, setPeriod] = useState<Period>('30d')
  return <>
    <p><Link className="text-link" to="/seller/wallet">View withdrawable balances and payouts</Link></p>
    <div className="analytics-tabs" aria-label="Analytics view">{(['performance', 'commission'] as const).map((value) => <Button key={value} className="button-secondary" aria-pressed={tab === value} onClick={() => setTab(value)}>{value === 'performance' ? 'Performance' : 'Commission ledger'}</Button>)}</div>
    {tab === 'performance' ? <>
      <div className="field analytics-filter"><label htmlFor="analytics-period">Performance period</label><select id="analytics-period" value={period} onChange={(event) => setPeriod(event.target.value as Period)}>{periods.map((value) => <option key={value} value={value}>{value === '1y' ? 'Last 365 days' : `Last ${value.slice(0, -1)} days`}</option>)}</select></div>
      <Performance key={period} period={period} />
    </> : <CommissionLedger />}
  </>
}
function Performance({ period }: { period: Period }) {
  const overviewCheck = useCallback((value: Overview) => validateOverview(value, period), [period])
  const overview = useOrderRead('/seller/analytics/overview?period=' + period, true, overviewCheck)
  const inventory = useOrderRead('/seller/analytics/inventory-health', true, validateInventoryHealth)
  return <>
    <section className="account-card analytics-wide"><h2>Sales overview</h2><p>Settlement amounts include recorded refund reversals. They are not your available wallet balance.</p><ReadState resource={overview} label="sales overview">{overview.data && <>
      <Metrics rows={[["Gross after refunds", analyticsMoney(overview.data.gross_revenue)], ['Commission after reversals', analyticsMoney(overview.data.commission_paid)], ['Net earnings', analyticsMoney(overview.data.net_earnings)], ['Settled brand shipments', overview.data.order_count], ['Average settled shipment', analyticsMoney(overview.data.avg_order_value)], ['Qualifying units ordered', overview.data.units_sold], ['Tracked product views', overview.data.total_views], ['Settlements / tracked views', `${overview.data.conversion_rate}%`]]} />
      <p className="muted">Earnings follow settlement dates. Units follow qualifying order dates and are not refund-adjusted. The view ratio is not a unique-customer conversion rate.</p>
    </>}</ReadState></section>
    <Revenue period={period} /><Products period={period} />
    <section className="account-card analytics-wide"><h2>Current stock health</h2><p>Current active variants, independent of the selected period. Available units exclude reservations. Low stock is included in in-stock variants.</p><ReadState resource={inventory} label="stock health">{inventory.data && <Metrics rows={[["Active variants", inventory.data.total_variants], ['In stock', inventory.data.in_stock], ['Low stock', inventory.data.low_stock], ['Out of stock', inventory.data.out_of_stock], ['Available units', inventory.data.total_units]]} />}</ReadState><p><Link className="text-link" to="/seller/inventory">Manage inventory</Link></p></section>
  </>
}
function Revenue({ period }: { period: Period }) {
  const [granularity, setGranularity] = useState<Granularity>('day')
  const check = useCallback((value: RevenueSeries) => validateRevenue(value, period, granularity), [period, granularity])
  const resource = useOrderRead(`/seller/analytics/revenue?period=${period}&granularity=${granularity}`, true, check)
  return <section className="account-card analytics-wide"><h2>Settlement trend</h2>
    <div className="field analytics-filter"><label htmlFor="analytics-interval">Group settlements by</label><select id="analytics-interval" value={granularity} onChange={(event) => setGranularity(event.target.value as Granularity)}><option value="day">Day</option><option value="week">Week</option><option value="month">Month</option></select></div>
    <p>UTC bucket start dates; only buckets with recorded settlements are listed. Amounts reflect subsequent refund reversals, not cash movements on the refund date.</p>
    <ReadState resource={resource} label="settlement trend">{resource.data && (resource.data.data.length ? <div className="analytics-table-wrap" tabIndex={0} role="region" aria-label="Settlement trend table"><table className="analytics-table"><caption>Settlement amounts after refunds</caption><thead><tr><th scope="col">Bucket start</th><th scope="col">Gross</th><th scope="col">Commission</th><th scope="col">Net</th><th scope="col">Shipments</th></tr></thead><tbody>{resource.data.data.map((row) => <tr key={row.date}><th scope="row">{row.date}</th><td>{analyticsMoney(row.gross)}</td><td>{analyticsMoney(row.commission)}</td><td>{analyticsMoney(row.net)}</td><td>{row.orders}</td></tr>)}</tbody></table></div> : <EmptyState title="No settlements in this period"><p>Settled sales will appear here when recorded.</p></EmptyState>)}</ReadState>
  </section>
}
function Products({ period }: { period: Period }) {
  const [ranking, setRanking] = useState<Ranking>('revenue')
  const check = useCallback((value: TopProducts) => validateTopProducts(value, period, ranking), [period, ranking])
  const resource = useOrderRead(`/seller/analytics/top-products?period=${period}&sort_by=${ranking}&limit=10`, true, check)
  return <section className="account-card analytics-wide"><h2>Top products</h2>
    <div className="field analytics-filter"><label htmlFor="analytics-ranking">Rank products by</label><select id="analytics-ranking" value={ranking} onChange={(event) => setRanking(event.target.value as Ranking)}><option value="revenue">Order value</option><option value="units">Units</option><option value="views">Lifetime views</option></select></div>
    <p>Up to 10 products. Order value and units use qualifying orders within the period, before refund adjustments. Views and ratings are lifetime figures.</p>
    <ReadState resource={resource} label="top products">{resource.data && (resource.data.data.length ? <ol className="analytics-products">{resource.data.data.map((row) => <li key={row.product_id}><h3><Link className="text-link" to={`/seller/products/${row.product_id}/edit`}>{row.product_name}</Link></h3><Metrics rows={[["Order value", analyticsMoney(row.revenue)], ['Units', row.units_sold], ['Lifetime views', row.views], ['Lifetime rating', `${row.avg_rating} / 5`]]} /></li>)}</ol> : <EmptyState title="No products to rank"><p>Your products will appear here as data becomes available.</p></EmptyState>)}</ReadState>
  </section>
}
function CommissionLedger() {
  const [page, setPage] = useState(1)
  const check = useCallback((value: CommissionPage) => validateCommission(value, page), [page])
  const resource = useOrderRead(`/seller/wallet/commission-breakdown?page=${page}`, true, check)
  const data = resource.data, summary = data?.summary
  const pages = data ? Math.max(1, Math.ceil(data.total / 25)) : 1
  return <section className="account-card analytics-wide"><h2>All-time commission ledger</h2><p>Totals cover all recorded settlements, not just this page. Release records are not bank payout confirmations. <Link className="text-link" to="/seller/wallet">Check your wallet for withdrawable balances.</Link></p>
    <ReadState resource={resource} label="commission ledger">{data && summary && <>
      <Metrics rows={[["Gross after refunds", analyticsMoney(summary.total_gross)], ['Commission after reversals', analyticsMoney(summary.total_commission)], ['Net earnings', analyticsMoney(summary.total_net)]]} />
      <details><summary>All-time refund and recovery totals</summary><Metrics rows={[["Original gross", analyticsMoney(summary.original_gross)], ['Original commission', analyticsMoney(summary.original_commission)], ['Original seller earnings', analyticsMoney(summary.original_net)], ['Gross refunded', analyticsMoney(summary.total_refunded_gross)], ['Commission reversed', analyticsMoney(summary.total_reversed_commission)], ['Seller earnings reversed', analyticsMoney(summary.total_reversed_seller)], ['Recovered from wallet', analyticsMoney(summary.total_recovered_seller)], ['Offset against settlement', analyticsMoney(summary.total_settlement_offset)], ['Platform-covered shortfall', analyticsMoney(summary.total_platform_shortfall)]]} /></details>
      {!data.data.length && <EmptyState title="No settlement entries on this page"><p>Recorded settlements will appear here. Use a previous page if the ledger has changed.</p></EmptyState>}
      {data.data.map((row) => <CommissionRow key={row.id} row={row} />)}
      <nav className="analytics-tabs" aria-label="Commission pages"><Button className="button-secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous commission page</Button><p role="status">Page {page} of {pages} · {data.total} entries</p><Button className="button-secondary" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>Next commission page</Button></nav>
    </>}</ReadState>
  </section>
}
function CommissionRow({ row }: { row: CommissionEntry }) {
  return <article className="analytics-entry"><h3>Settlement recorded {orderDate(row.settled_at)}</h3><p><Link className="text-link" to={`/seller/orders/${row.seller_order_id}`}>View brand shipment {row.seller_order_id}</Link></p>
    <Metrics rows={[["Gross after refunds", analyticsMoney(row.gross_amount)], ['Commission after reversals', analyticsMoney(row.commission_amount)], ['Net earnings', analyticsMoney(row.seller_amount)], ['Original commission rate', `${Number((row.commission_rate * 100).toFixed(2))}%`]]} />
    <p>{row.released_at ? `Release recorded ${orderDate(row.released_at)}` : 'No release recorded'}</p>
    <details><summary>Settlement refund details</summary><p>Ledger reference: {row.id}</p><Metrics rows={[["Original gross", analyticsMoney(row.original_gross_amount)], ['Original commission', analyticsMoney(row.original_commission_amount)], ['Original seller earnings', analyticsMoney(row.original_seller_amount)], ['Gross refunded', analyticsMoney(row.refunded_gross_amount)], ['Commission reversed', analyticsMoney(row.reversed_commission_amount)], ['Seller earnings reversed', analyticsMoney(row.reversed_seller_amount)], ['Recovered from wallet', analyticsMoney(row.recovered_seller_amount)], ['Offset against settlement', analyticsMoney(row.settlement_offset_amount)], ['Platform-covered shortfall', analyticsMoney(row.platform_shortfall_amount)]]} /></details>
  </article>
}
