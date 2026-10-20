import { Route, Routes } from 'react-router'
import { AuthProvider } from './auth/AuthProvider'
import { Layout } from './components/Layout'
import { ErrorBoundary, NotFound } from './components/ui'
import { AccountPage, AuthPage, VerifyEmailPage } from './pages/AuthPages'
import { BrandPage, BrandsPageView, CataloguePageView, HomePage } from './pages/Storefront'
import { ProductPage } from './pages/ProductPage'
import { BagPage } from './pages/BagPage'
import { CartProvider } from './cart/CartProvider'

export default function App() {
  return <ErrorBoundary><AuthProvider><CartProvider><Routes>
    <Route element={<Layout />}>
      <Route index element={<HomePage />} />
      <Route path="clothing" element={<CataloguePageView />} />
      <Route path="brands" element={<BrandsPageView />} />
      <Route path="brands/:slug" element={<BrandPage />} />
      <Route path="products/:id" element={<ProductPage />} />
      <Route path="bag" element={<BagPage />} />
      <Route path="login" element={<AuthPage key="login" mode="login" />} />
      <Route path="register" element={<AuthPage key="register" mode="register" />} />
      <Route path="forgot-password" element={<AuthPage key="forgot" mode="forgot" />} />
      <Route path="reset-password" element={<AuthPage key="reset" mode="reset" />} />
      <Route path="account" element={<AccountPage />} />
      <Route path="verify-email" element={<VerifyEmailPage />} />
      <Route path="auth/verify-email" element={<VerifyEmailPage />} />
      <Route path="auth/callback" element={<AccountPage />} />
      <Route path="help" element={<section className="container page help-page">
        <p className="eyebrow">WearHowZ help</p><h1>A little help,<br /><em>when you need it.</em></h1>
        <details open><summary>Shopping across brands</summary><p>Your bag can contain pieces from several labels. Each brand fulfils its own items, so shipments can have different statuses.</p></details>
        <details><summary>Returns</summary><p>Return conditions belong to the individual brand. Review the policy on the brand page before ordering.</p></details>
        <details><summary>About this first build</summary><p>Browsing and email sign-in are connected. Purchasing, saved pieces, account management and portals are still being built. No payments can be made from this preview.</p></details>
      </section>} />
      <Route path="*" element={<NotFound />} />
    </Route>
  </Routes></CartProvider></AuthProvider></ErrorBoundary>
}
