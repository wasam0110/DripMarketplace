import { client } from './client'

export const adminApi = {
  dashboard:      (period = 'month') => client.get('/admin/dashboard', { params: { period } }).then(r => r.data),
  sellers:        (p?: object)       => client.get('/admin/sellers', { params: p }).then(r => r.data),
  approveSeller:  (id: string)       => client.post(`/admin/sellers/${id}/approve`, {}).then(r => r.data),
  rejectSeller:   (id: string, b: object) => client.post(`/admin/sellers/${id}/reject`, b).then(r => r.data),
  orders:         (p?: object)       => client.get('/admin/orders', { params: p }).then(r => r.data),
  codQueue:       ()                 => client.get('/admin/cod-queue').then(r => r.data),
  verifyCod:      (id: string, b: object) => client.post(`/admin/cod-queue/${id}/verify`, b).then(r => r.data),
  payouts:        (p?: object)       => client.get('/admin/payouts', { params: p }).then(r => r.data),
  approvePayout:  (id: string, b: object) => client.post(`/admin/payouts/${id}/approve`, b).then(r => r.data),
  settings:       ()                 => client.get('/admin/settings').then(r => r.data),
  updateSettings: (b: object)        => client.patch('/admin/settings', b).then(r => r.data),
}
