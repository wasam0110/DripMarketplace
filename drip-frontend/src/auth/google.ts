/** Only the configured Google authorization endpoint may receive a browser redirect. */
export function googleAuthorizationUrl(value: unknown): string {
  if (typeof value !== 'string') throw new Error('The sign-in provider returned an unexpected address.')
  const target = new URL(value)
  if (target.origin !== 'https://accounts.google.com' || target.pathname !== '/o/oauth2/v2/auth' || target.username || target.password || target.hash) throw new Error('The sign-in provider returned an unexpected address.')
  return target.href
}
