import { Component, useId, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from 'react'
import { Link } from 'react-router'
import { ApiError } from '../api/client'

export function Button({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" className={`button ${className}`} {...props} />
}

export function Field({ label, hint, error, id, ...props }: InputHTMLAttributes<HTMLInputElement> & {
  label: string; hint?: string; error?: string
}) {
  const generatedId = useId()
  const fieldId = id ?? generatedId
  const message = error ?? hint
  return <div className="field">
    <label htmlFor={fieldId}>{label}</label>
    <input {...props} id={fieldId} aria-invalid={error ? true : undefined}
      aria-describedby={message ? `${fieldId}-help` : undefined} />
    {message && <small id={`${fieldId}-help`} className={error ? 'field-error' : 'muted'}>{message}</small>}
  </div>
}

export function ErrorNotice({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : 'Something went wrong. Please try again.'
  return <div className="notice error-notice" role="alert">
    <p>{message}</p>
    {error instanceof ApiError && error.retryAfter && <small>Please wait before retrying (Retry-After: {error.retryAfter}).</small>}
    {error instanceof ApiError && error.requestId && <small>Reference: {error.requestId}</small>}
  </div>
}

export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return <div className="empty-state">
    <span className="monogram" aria-hidden="true">W</span>
    <h2>{title}</h2>
    <div className="muted">{children}</div>
  </div>
}

export function Arrow() { return <span aria-hidden="true">↗</span> }

export function Icon({ name }: { name: 'menu' | 'search' | 'account' | 'close' | 'bag' }) {
  const paths = {
    bag: <><path d="M5 7h14l1 14H4L5 7Z" /><path d="M8 8V6a4 4 0 0 1 8 0v2" /></>,
    menu: <path d="M4 6h16M4 12h16M4 18h16" />,
    search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
    account: <><circle cx="12" cy="7" r="3.5" /><path d="M4.5 21v-2a7.5 7.5 0 0 1 15 0v2" /></>,
    close: <path d="m5 5 14 14M19 5 5 19" />,
  }
  return <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">{paths[name]}</svg>
}

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (this.state.failed) return <main className="container page">
      <EmptyState title="We couldn’t load that."><p>Please reload the page to try again.</p></EmptyState>
      <Button onClick={() => window.location.reload()}>Reload page</Button>
    </main>
    return this.props.children
  }
}

export function NotFound() {
  return <section className="container page">
    <EmptyState title="This piece of the story is missing.">
      <p>The page may have moved. There’s plenty more to discover.</p>
      <Link className="text-link" to="/">Back to WearHowZ <Arrow /></Link>
    </EmptyState>
  </section>
}
