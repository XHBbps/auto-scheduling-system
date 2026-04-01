const toFiniteNumber = (value: number | string | null | undefined): number | null => {
  if (value === null || value === undefined || value === '') return null
  const numericValue = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(numericValue) ? numericValue : null
}

export const normalizePartCycleDays = (value: number | string | null | undefined): number => {
  const numericValue = toFiniteNumber(value)
  return numericValue === null ? 0 : Math.round(numericValue)
}

export const normalizePartUnitCycleDays = (value: number | string | null | undefined): number => {
  const numericValue = toFiniteNumber(value)
  if (numericValue === null) return 0
  return Math.round((numericValue + Number.EPSILON) * 10) / 10
}

export const formatPartCycleDays = (value: number | string | null | undefined): string => {
  const numericValue = toFiniteNumber(value)
  return numericValue === null ? '-' : String(normalizePartCycleDays(numericValue))
}

export const formatPartUnitCycleDays = (value: number | string | null | undefined): string => {
  const numericValue = toFiniteNumber(value)
  return numericValue === null ? '-' : normalizePartUnitCycleDays(numericValue).toFixed(1)
}
