export function whatsappLink(phone: string, message: string): string {
  const clean = phone.replace(/\D/g, '')
  const e164  = clean.startsWith('92') ? clean : `92${clean.replace(/^0/, '')}`
  return `https://wa.me/${e164}?text=${encodeURIComponent(message)}`
}
