interface IndicatorLabel {
  name: string
  description: string
  unit: string
}

const labels: Record<string, IndicatorLabel> = {
  'DT.DOD.DECT.GN.ZS': {
    name: 'External debt',
    description: 'External debt outstanding as a share of gross national income.',
    unit: 'Share of GNI (%)',
  },
  'DT.TDS.DECT.EX.ZS': {
    name: 'Debt service',
    description: 'External debt payments as a share of exports and primary income.',
    unit: 'Share of exports (%)',
  },
  'FI.RES.TOTL.MO': {
    name: 'Foreign reserves',
    description: 'International reserves measured in months of imports.',
    unit: 'Months of imports',
  },
  'NY.GDP.MKTP.CD': {
    name: 'GDP',
    description: 'Total economic output in current US dollars.',
    unit: 'Current US dollars',
  },
  'NY.GDP.MKTP.KD.ZG': {
    name: 'GDP growth',
    description: 'How much an economy grew or shrank in a year.',
    unit: 'Annual change (%)',
  },
  'NY.GDP.PCAP.CD': {
    name: 'GDP per person',
    description:
      'The size of an economy divided by its population, in current US dollars.',
    unit: 'US dollars per person',
  },
  'FP.CPI.TOTL.ZG': {
    name: 'Inflation',
    description: 'How much consumer prices changed over a year.',
    unit: 'Annual change (%)',
  },
  'NE.EXP.GNFS.ZS': {
    name: 'Exports',
    description: 'Goods and services sold abroad, as a share of the economy.',
    unit: 'Share of GDP (%)',
  },
  'NE.IMP.GNFS.ZS': {
    name: 'Imports',
    description:
      'Goods and services bought from abroad, as a share of the economy.',
    unit: 'Share of GDP (%)',
  },
  'BN.CAB.XOKA.GD.ZS': {
    name: 'Current account balance',
    description:
      'The balance of trade, income, and transfers with the rest of the world.',
    unit: 'Share of GDP (%)',
  },
}

export function getIndicatorLabel(
  code: string,
  metadata?: { name: string; definition: string; unit: string },
): IndicatorLabel {
  return labels[code] || {
    name: metadata?.name || code,
    description: metadata?.definition || '',
    unit: metadata?.unit || '',
  }
}

export function formatIndicatorValue(
  value: number | null,
  indicator: string,
  unit?: string,
): string {
  if (value === null) return 'No data'
  if (indicator === 'default-risk') return `${(value * 100).toFixed(1)}%`

  const formatted = value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
  })
  if (indicator === 'NY.GDP.PCAP.CD') return `$${formatted}`
  const displayUnit = unit || getIndicatorLabel(indicator).unit
  if (displayUnit.includes('%') || /percent/i.test(displayUnit)) return `${formatted}%`
  return displayUnit ? `${formatted} ${displayUnit}` : formatted
}
