export const SAVED_KEY = 'wearhowz.saved-pieces.v1'
export const MAX_SAVED = 100
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/** Persist identifiers only. Names, images, stock and prices are always read live. */
export function parseSaved(raw: string | null): string[] {
  if (raw === null) return []
  const value: unknown = JSON.parse(raw)
  if (!Array.isArray(value) || value.length > MAX_SAVED || value.some((id) => typeof id !== 'string' || !uuid.test(id))) throw new Error('Invalid saved pieces.')
  const ids = value.map((id: string) => id.toLowerCase())
  if (new Set(ids).size !== ids.length) throw new Error('Duplicate saved pieces.')
  return ids
}
export function readSaved() { return parseSaved(localStorage.getItem(SAVED_KEY)) }
export function changeSaved(current: string[], id: string, wanted: boolean) {
  if (!uuid.test(id)) throw new Error('This piece cannot be saved.')
  const normalized = id.toLowerCase()
  const next = current.filter((entry) => entry !== normalized)
  if (wanted) next.unshift(normalized)
  if (next.length > MAX_SAVED) throw new Error(`You can save up to ${MAX_SAVED} pieces on this device. Remove a piece first.`)
  return next
}
export function writeSaved(ids: string[]) {
  const raw = JSON.stringify(ids)
  parseSaved(raw)
  if (ids.length) localStorage.setItem(SAVED_KEY, raw)
  else localStorage.removeItem(SAVED_KEY)
}
