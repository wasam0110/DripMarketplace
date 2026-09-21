import { isAxiosError } from 'axios'

export function getErrorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    return err.response?.data?.error?.message || err.message || 'Something went wrong'
  }
  if (err instanceof Error) return err.message
  return 'Something went wrong'
}

export function getFieldErrors(err: unknown): Record<string, string> {
  if (isAxiosError(err)) {
    return err.response?.data?.error?.fields || {}
  }
  return {}
}
