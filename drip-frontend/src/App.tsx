import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { CustomerLayout } from '@/components/layout/CustomerLayout'
import { SellerLayout }   from '@/components/layout/SellerLayout'
import { AdminLayout }    from '@/components/layout/AdminLayout'
import type { UserRole }  from '@/types/user'

// Lazy-load pages for code splitting
const HomePage           = lazy(() => import('@/pages/customer/HomePage'))
const CataloguePage      = lazy(() => import('@/pages/customer/CataloguePage'))
const ProductPage        = lazy(() => import('@/pages/customer/ProductPage'))
const CheckoutPage       = lazy(() => import('@/pages/customer/CheckoutPage'))
const OrderSuccessPage   = lazy(() => import('@/pages/customer/OrderSuccessPage'))
const AccountPage        = lazy(() => import('@/pages/customer/AccountPage'))
const BrandPage          = lazy(() => import('@/pages/customer/BrandPage'))

const ContactPage    = lazy(() => import('@/pages/customer/ContactPage'))
const ReturnsPage    = lazy(() => import('@/pages/customer/ReturnsPage'))
const TrackOrderPage = lazy(() => import('@/pages/customer/TrackOrderPage'))

const LoginPage          = lazy(() => import('@/pages/auth/LoginPage'))
const RegisterPage       = lazy(() => import('@/pages/auth/RegisterPage'))
const ForgotPasswordPage = lazy(() => import('@/pages/auth/ForgotPasswordPage'))
const SellerRegisterPage = lazy(() => import('@/pages/seller/RegisterPage'))

const SellerDashboard    = lazy(() => import('@/pages/seller/DashboardPage'))
const SellerProducts     = lazy(() => import('@/pages/seller/ProductsPage'))
const SellerOrders       = lazy(() => import('@/pages/seller/OrdersPage'))
const SellerWallet       = lazy(() => import('@/pages/seller/WalletPage'))
const SellerSettings     = lazy(() => import('@/pages/seller/SettingsPage'))

const AdminDashboard     = lazy(() => import('@/pages/admin/DashboardPage'))
const AdminBrands        = lazy(() => import('@/pages/admin/BrandsPage'))
const AdminCODQueue      = lazy(() => import('@/pages/admin/CODQueuePage'))
const AdminPayouts       = lazy(() => import('@/pages/admin/PayoutsPage'))
const AdminOrders        = lazy(() => import('@/pages/admin/OrdersPage'))
const AdminAnalytics     = lazy(() => import('@/pages/admin/AnalyticsPage'))
const AdminSettings      = lazy(() => import('@/pages/admin/SettingsPage'))

function Loader() {
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center">
      <span className="font-mono text-muted text-sm animate-pulse">loading…</span>
    </div>
  )
}

function RequireAuth({ role, children }: { role?: UserRole; children: React.ReactNode }) {
  const user = useAuthStore(s => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role) return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Suspense fallback={<Loader />}>
      <Routes>
        {/* ── Public / storefront ── */}
        <Route element={<CustomerLayout />}>
          <Route path="/"             element={<HomePage />} />
          <Route path="/shop"         element={<CataloguePage />} />
          <Route path="/product/:slug" element={<ProductPage />} />
          <Route path="/brand/:slug"  element={<BrandPage />} />
          <Route path="/contact" element={<ContactPage />} />
          <Route path="/returns" element={<ReturnsPage />} />
          <Route path="/track"   element={<TrackOrderPage />} />
          <Route path="/checkout"               element={<CheckoutPage />} />
          <Route path="/order/success/:orderId" element={<OrderSuccessPage />} />
          <Route path="/account/*"              element={
            <RequireAuth><AccountPage /></RequireAuth>
          } />
        </Route>

        {/* ── Auth ── */}
        <Route path="/login"           element={<LoginPage />} />
        <Route path="/register"        element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/sell"            element={<SellerRegisterPage />} />

        {/* ── Seller dashboard ── */}
        <Route path="/dashboard" element={
          <RequireAuth role="seller"><SellerLayout /></RequireAuth>
        }>
          <Route index              element={<SellerDashboard />} />
          <Route path="products"    element={<SellerProducts />} />
          <Route path="orders"      element={<SellerOrders />} />
          <Route path="wallet"      element={<SellerWallet />} />
          <Route path="settings"    element={<SellerSettings />} />
        </Route>

        {/* ── Admin ── */}
        <Route path="/admin" element={
          <RequireAuth role="admin"><AdminLayout /></RequireAuth>
        }>
          <Route index              element={<AdminDashboard />} />
          <Route path="brands"      element={<AdminBrands />} />
          <Route path="orders"      element={<AdminOrders />} />
          <Route path="cod-queue"   element={<AdminCODQueue />} />
          <Route path="payouts"     element={<AdminPayouts />} />
          <Route path="analytics"   element={<AdminAnalytics />} />
          <Route path="settings"    element={<AdminSettings />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
