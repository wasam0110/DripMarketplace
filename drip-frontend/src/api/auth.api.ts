import { client } from './client'
import type { User } from '@/types/user'

export interface LoginPayload   { email: string; password: string }
export interface RegisterPayload { first_name: string; last_name: string; email: string; password: string; phone?: string }
export interface AuthResponse   { access_token: string; user: User }

export const authApi = {
  login:           (b: LoginPayload)    => client.post<AuthResponse>('/auth/login', b).then(r => r.data),
  register:        (b: RegisterPayload) => client.post<{ message: string }>('/auth/register', b).then(r => r.data),
  logout:          ()                   => client.post('/auth/logout', {}).then(r => r.data),
  refresh:         ()                   => client.post<{ access_token: string }>('/auth/refresh', {}).then(r => r.data),
  me:              ()                   => client.get<User>('/auth/me').then(r => r.data),
  forgotPassword:  (b: { email: string }) => client.post('/auth/forgot-password', b).then(r => r.data),
  resetPassword:   (b: { token: string; new_password: string }) => client.post('/auth/reset-password', b).then(r => r.data),
  changePassword:  (b: { current_password: string; new_password: string; confirm_password: string }) =>
                     client.post('/customers/me/change-password', b).then(r => r.data),
}
