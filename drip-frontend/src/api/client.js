const API_URL = (import.meta.env.VITE_API_URL || 'https://api.drip.pk/api/v1').replace(/\/$/, '')
let refreshing = null
const token = () => sessionStorage.getItem('drip_access_token')
const requestId = () => `web_${crypto.randomUUID?.() || Math.random().toString(36).slice(2)}`

async function raw(path, options = {}) {
  const headers = new Headers(options.headers || {})
  if (!headers.has('Content-Type') && options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  headers.set('X-Request-ID', requestId())
  const access = token(); if (access) headers.set('Authorization', `Bearer ${access}`)
  const response = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: 'include' })
  if (response.status === 401 && !options._retried && path !== '/auth/refresh') {
    refreshing ||= raw('/auth/refresh', { method: 'POST', _retried: true }).then(r => r.access_token).finally(() => { refreshing = null })
    try { const next = await refreshing; sessionStorage.setItem('drip_access_token', next); return raw(path, { ...options, _retried: true }) } catch { sessionStorage.removeItem('drip_access_token') }
  }
  if (!response.ok) { let body = {}; try { body = await response.json() } catch {} ; const error = new Error(body?.error?.message || `API request failed (${response.status})`); error.status = response.status; error.fields = body?.error?.fields; throw error }
  if (response.status === 204) return null
  return response.json()
}
export const api = {
  get: (path, params) => raw(`${path}${params ? `?${new URLSearchParams(Object.entries(params).filter(([,v])=>v!==undefined&&v!==''))}` : ''}`),
  post: (path, body) => raw(path, { method:'POST', body: body instanceof FormData ? body : JSON.stringify(body) }),
  put: (path, body) => raw(path, { method:'PUT', body: JSON.stringify(body) }),
  patch: (path, body) => raw(path, { method:'PATCH', body: JSON.stringify(body) }),
  delete: path => raw(path, { method:'DELETE' }),
}
export const endpoint = {
  auth: { register:b=>api.post('/auth/register',b), login:b=>api.post('/auth/login',b), verifyEmail:t=>api.get('/auth/verify-email',{token:t}), refresh:()=>api.post('/auth/refresh',{}), logout:()=>api.post('/auth/logout',{}), me:()=>api.get('/auth/me'), forgotPassword:b=>api.post('/auth/forgot-password',b), resetPassword:b=>api.post('/auth/reset-password',b), changePassword:b=>api.post('/auth/change-password',b), setup2fa:()=>api.post('/auth/setup-2fa',{}), verify2fa:b=>api.post('/auth/setup-2fa/verify',b), google:()=>api.get('/auth/google') },
  products: { list:p=>api.get('/products',p), detail:id=>api.get(`/products/${id}`), slug:s=>api.get(`/products/slug/${s}`), variants:id=>api.get(`/products/${id}/variants`), suggestions:q=>api.get('/products/search/suggestions',{q}), reviews:id=>api.get(`/products/${id}/reviews`), submitReview:(id,b)=>api.post(`/products/${id}/reviews`,b) },
  customer: { me:()=>api.get('/auth/me'), orders:p=>api.get('/orders',p), cart:()=>api.get('/cart') },
  cart: { get:()=>api.get('/cart'), add:b=>api.post('/cart',b), update:(id,b)=>api.patch(`/cart/${id}`,b), remove:id=>api.delete(`/cart/${id}`), clear:()=>api.post('/cart/clear',{}), sync:b=>api.post('/cart/sync',b) },
  orders: { create:b=>api.post('/orders',b), guest:b=>api.post('/orders/guest',b), list:p=>api.get('/orders',p), detail:id=>api.get(`/orders/${id}`), track:(number,email)=>api.get(`/orders/number/${number}`,{email}), cancel:(id,b)=>api.post(`/orders/${id}/cancel`,b), validateCoupon:b=>api.post('/coupons/validate',b) },
  payments: { initiate:b=>api.post('/payments/initiate',b), status:id=>api.get(`/payments/${id}/status`), retry:(id,b)=>api.post(`/payments/${id}/retry`,b), gatewayStatus:()=>api.get('/payments/gateway-status'), list:p=>api.get('/payments',p), refund:(id,b)=>api.post(`/payments/${id}/refund`,b) },
  seller: { register:b=>api.post('/seller/register',b), profile:()=>api.get('/seller/me'), update:b=>api.patch('/seller/me',b), logo:b=>api.post('/seller/logo',b), dashboard:p=>api.get('/seller/dashboard',{period:p}), slotPrice:n=>api.get('/seller/register/slot-price',{extra_slots:n}), purchaseSlots:b=>api.post('/seller/slots/purchase',b), products:p=>api.get('/seller/products',p), createProduct:b=>api.post('/seller/products',b), updateProduct:(id,b)=>api.put(`/seller/products/${id}`,b), deleteProduct:id=>api.delete(`/seller/products/${id}`), publish:id=>api.post(`/seller/products/${id}/publish`,{}), unpublish:id=>api.post(`/seller/products/${id}/unpublish`,{}), uploadImages:(id,b)=>api.post(`/seller/products/${id}/images`,b), orders:p=>api.get('/seller/orders',p), order:id=>api.get(`/seller/orders/${id}`), updateOrder:(id,b)=>api.put(`/seller/orders/${id}/status`,b), wallet:()=>api.get('/seller/wallet'), transactions:p=>api.get('/seller/wallet/transactions',p), withdraw:b=>api.post('/seller/wallet/withdraw',b), payouts:p=>api.get('/seller/wallet/payouts',p), commission:p=>api.get('/seller/wallet/commission-breakdown',p), bankAccounts:()=>api.get('/seller/bank-accounts'), addBankAccount:b=>api.post('/seller/bank-accounts',b), deleteBankAccount:id=>api.delete(`/seller/bank-accounts/${id}`), revenue:p=>api.get('/seller/analytics/revenue',p) },
  admin: { dashboard:p=>api.get('/admin/dashboard',{period:p}), sellers:p=>api.get('/admin/sellers',p), seller:id=>api.get(`/admin/sellers/${id}`), approveSeller:id=>api.post(`/admin/sellers/${id}/approve`,{}), rejectSeller:(id,b)=>api.post(`/admin/sellers/${id}/reject`,b), suspendSeller:(id,b)=>api.post(`/admin/sellers/${id}/suspend`,b), reinstateSeller:id=>api.post(`/admin/sellers/${id}/reinstate`,{}), orders:p=>api.get('/admin/orders',p), codQueue:()=>api.get('/admin/cod-queue'), verifyCod:(id,b)=>api.post(`/admin/cod-queue/${id}/verify`,b), cancelCod:(id,b)=>api.post(`/admin/cod-queue/${id}/cancel`,b), payouts:p=>api.get('/admin/payouts',p), approvePayout:(id,b)=>api.post(`/admin/payouts/${id}/approve`,b), completePayout:(id,b)=>api.post(`/admin/payouts/${id}/complete`,b), rejectPayout:(id,b)=>api.post(`/admin/payouts/${id}/reject`,b), banners:()=>api.get('/admin/content/banners'), createBanner:b=>api.post('/admin/content/banners',b), deleteBanner:id=>api.delete(`/admin/content/banners/${id}`), settings:()=>api.get('/admin/settings'), updateSettings:b=>api.patch('/admin/settings',b), products:p=>api.get('/admin/products',p), hideProduct:id=>api.post(`/admin/products/${id}/hide`,{}) },
}
export { API_URL }
