export type RecurringSeries = Record<string, any>

const cadenceMultipliers: Record<string, number> = {
  weekly: 4.33,
  biweekly: 2.17,
  monthly: 1,
  quarterly: 0.33,
  semi_annual: 0.167,
  annual: 0.083,
}

const cadenceLabels: Record<string, string> = {
  weekly: 'Weekly',
  biweekly: 'Bi-weekly',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  semi_annual: 'Semi-Annual',
  annual: 'Annual',
}

export function getSeriesId(item: RecurringSeries) {
  return item.id || item.series_id
}

export function getMerchantName(item: RecurringSeries) {
  return item.display_name || item.merchant || item.merchant_name || item.payee || item.name || 'Unknown'
}

export function formatAmount(amount: number) {
  return `$${Math.abs(amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function getCadenceLabel(item: RecurringSeries) {
  const cadenceKey = typeof item.cadence === 'string' ? item.cadence : ''
  return item.cadence_label || cadenceLabels[cadenceKey] || 'Monthly'
}

export function getMonthlyAmount(item: RecurringSeries) {
  const amount = Math.abs(item.amount_mean || item.amount || 0)
  const multiplier = cadenceMultipliers[item.cadence] || 1
  return amount * multiplier
}

export function getAmountVariance(item: RecurringSeries) {
  const amount = Math.abs(item.amount_mean || item.amount || 0)
  const sd = Math.abs(item.amount_sd || 0)
  if (!amount) return 0
  return sd / Math.max(1, amount)
}

export function sumMonthly(items: RecurringSeries[]) {
  return items.reduce((sum, item) => sum + getMonthlyAmount(item), 0)
}
