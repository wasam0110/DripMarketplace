// Only server-returned roles select a destination; URL parameters cannot grant access.
export function accountDestination(role: string | undefined): string {
  if (role === 'seller') return '/seller'
  if (role === 'admin') return '/admin'
  return '/account'
}
