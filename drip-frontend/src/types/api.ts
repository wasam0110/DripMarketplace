export interface ApiError {
  error: { code: string; message: string; fields?: Record<string, string[]> }
}
export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  pages: number
}
export interface CursorPage<T> {
  data: T[]
  next_cursor: string | null
  has_more: boolean
}
