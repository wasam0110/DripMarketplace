export function pkr(amount: number): string {
  return `PKR ${Math.round(amount).toLocaleString('en-PK')}`
}
export function discount(original: number, sale: number): number {
  return Math.round(((original - sale) / original) * 100)
}
