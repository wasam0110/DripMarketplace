import { useCallback, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { useAuth } from '../auth/AuthProvider'
import { accountDestination } from '../auth/destination'
import { Button, EmptyState, ErrorNotice } from '../components/ui'
import { useOrderRead } from '../orders/api'
import { analyticsMoney, periods, validatePlatform, validateRevenue, validateTopSellers, type Granularity, type Period, type PlatformAnalytics, type RevenueSeries, type TopSellers } from './analytics'
import '../seller/analytics.css'

export function AdminAnalyticsPage() {
  const { user, loading, error } = useAuth()
  if (loading) return <section className="container page"><h1>Admin analytics</h1><p role="status">Checking your session…</p></section>
  if (error || !user) return <section className="container page"><h1>Sign in to view admin analytics</h1>{error && <ErrorNotice error={new Error(error)} />}<Link to="/login">Sign in</Link></section>
  if (user.role !== 'admin') return <section className="container page"><h1>An administrator account is required</h1><Link to={accountDestination(user.role)}>Return to your workspace</Link></section>
  if (!user.has_verified_email) return <section className="container page"><h1>Verify your email first</h1><Link to="/account">Manage your account</Link></section>
  return <section className="container page seller-analytics"><Link className="text-link" to="/admin">Back to admin workspace</Link><p className="eyebrow">WearHowZ · Platform management</p><h1>Admin analytics</h1><AnalyticsWorkspace key={user.id} /></section>
}
function ReadState({ resource, label, children }: { resource: { loading: boolean; error: unknown; retry: () => void }; label: string; children: ReactNode }) {
  return <div aria-busy={resource.loading}>{resource.loading && <p role="status">Loading {label}…</p>}{Boolean(resource.error) && <ErrorNotice error={resource.error} />}{children}<Button className="button-secondary" disabled={resource.loading} onClick={resource.retry}>Refresh {label}</Button></div>
}
function Metrics({ rows }: { rows: [string, string | number][] }) {
  return <dl className="analytics-metrics">{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
}
function AnalyticsWorkspace() {
  const [period, setPeriod] = useState<Period>('30d')
  const [granularity, setGranularity] = useState<Granularity>('day')
  const platformCheck = useCallback((value: PlatformAnalytics) => validatePlatform(value, period), [period])
  const revenueCheck = useCallback((value: RevenueSeries) => validateRevenue(value, period, granularity), [period, granularity])
  const sellersCheck = useCallback((value: TopSellers) => validateTopSellers(value, period), [period])
  const platform = useOrderRead(`/admin/analytics/platform?period=${period}`, true, platformCheck)
  const revenue = useOrderRead(`/admin/analytics/revenue?period=${period}&granularity=${granularity}`, true, revenueCheck)
  const sellers = useOrderRead(`/admin/analytics/top-sellers?period=${period}&limit=10`, true, sellersCheck)
  return <>
    <div className="field analytics-filter"><label htmlFor="admin-analytics-period">Reporting period</label><select id="admin-analytics-period" value={period} onChange={(event) => setPeriod(event.target.value as Period)}>{periods.map((value) => <option key={value} value={value}>{value === '1y' ? 'Last year' : `Last ${value.slice(0, -1)} days`}</option>)}</select></div>
    <section className="account-card analytics-wide"><h2>Platform overview</h2><p>GMV includes qualifying orders created in the selected period. Commission and slot revenue follow their recorded settlement or fee dates.</p><ReadState resource={platform} label="platform overview">{platform.data && <Metrics rows={[['Total GMV', analyticsMoney(platform.data.total_gmv)], ['Commission revenue', analyticsMoney(platform.data.commission_revenue)], ['Slot revenue', analyticsMoney(platform.data.slot_revenue)], ['Orders', platform.data.total_orders], ['New customers', platform.data.new_customers], ['Active sellers', platform.data.active_sellers], ['Average order value', analyticsMoney(platform.data.avg_order_value)], ['COD share', `${platform.data.cod_rate}%`], ['Cancellation rate', `${platform.data.cancellation_rate}%`]]} />}</ReadState></section>
    <section className="account-card analytics-wide"><h2>Revenue trend</h2><div className="field analytics-filter"><label htmlFor="admin-analytics-granularity">Group revenue by</label><select id="admin-analytics-granularity" value={granularity} onChange={(event) => setGranularity(event.target.value as Granularity)}><option value="day">Day</option><option value="week">Week</option><option value="month">Month</option></select></div><ReadState resource={revenue} label="revenue trend">{revenue.data && (revenue.data.data.length ? <div className="analytics-table-wrap" tabIndex={0} role="region" aria-label="Platform revenue trend table"><table className="analytics-table"><caption>Recorded platform revenue</caption><thead><tr><th scope="col">Bucket start</th><th scope="col">Gross</th><th scope="col">Commission</th><th scope="col">Net seller</th><th scope="col">Orders</th></tr></thead><tbody>{revenue.data.data.map((row) => <tr key={row.date}><th scope="row">{row.date}</th><td>{analyticsMoney(row.gross)}</td><td>{analyticsMoney(row.commission)}</td><td>{analyticsMoney(row.net)}</td><td>{row.orders}</td></tr>)}</tbody></table></div> : <EmptyState title="No revenue in this period"><p>Recorded settlements will appear here when available.</p></EmptyState>)}</ReadState></section>
    <section className="account-card analytics-wide"><h2>Top sellers</h2><p>Ranked by GMV in the selected period. This is an operational view, not a seller payout statement.</p><ReadState resource={sellers} label="top sellers">{sellers.data && (sellers.data.data.length ? <ol className="analytics-products">{sellers.data.data.map((row) => <li key={row.seller_id}><h3>{row.brand_name}</h3><Metrics rows={[['GMV', analyticsMoney(row.gmv)], ['Commission', analyticsMoney(row.commission)], ['Orders', row.order_count]]} /></li>)}</ol> : <EmptyState title="No sellers in this period"><p>Qualifying seller orders will appear here when available.</p></EmptyState>)}</ReadState></section>
  </>
}
