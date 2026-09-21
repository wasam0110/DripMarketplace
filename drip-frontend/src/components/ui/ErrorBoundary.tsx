import { Component, type ReactNode } from 'react'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean; error?: Error }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }
  static getDerivedStateFromError(error: Error): State { return { hasError: true, error } }
  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4 text-center p-8">
          <p className="text-muted text-sm font-mono">Something broke.</p>
          <p className="text-xs text-muted max-w-sm">{this.state.error?.message}</p>
          <button className="btn-outline text-xs" onClick={() => window.location.reload()}>Reload page</button>
        </div>
      )
    }
    return this.props.children
  }
}
