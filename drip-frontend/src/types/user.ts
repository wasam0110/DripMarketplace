export type UserRole = 'customer' | 'seller' | 'admin'
export interface User {
  id: string; email: string; first_name: string | null; last_name: string | null
  phone: string | null; avatar_url: string | null; role: UserRole
  has_verified_email: boolean; is_2fa_enabled: boolean
}
export interface Address {
  id: string; label: string | null; street: string
  city: string; province: string; is_default: boolean
}
