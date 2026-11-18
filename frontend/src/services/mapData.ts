import type { FeatureCollection, Geometry } from 'geojson'
import type { Country, MapData } from '../types/api'
import { isWorldBankIndicator, request } from './api'

export interface MapPlace {
  iso3: string
  name: string
}

export type WorldShapes = FeatureCollection<Geometry, MapPlace>

interface ValueRange {
  minimum: number
  maximum: number
}

export const mapColors = ['#d2e5f5', '#a5cce8', '#73add6', '#428ac0', '#1b5e97']
export const missingDataColor = '#e4e9ed'
export const riskBands = [
  { color: '#16a34a', label: 'Lower estimate', range: '<10%' },
  { color: '#eab308', label: 'Elevated estimate', range: '10–<50%' },
  { color: '#dc2626', label: 'Higher estimate', range: '≥50%' },
]

export function getRiskBand(value: number) {
  return riskBands[value < 0.1 ? 0 : value < 0.5 ? 1 : 2]
}

export async function loadWorldShapes(): Promise<WorldShapes> {
  const response = await fetch('/maps/world-countries.json')
  if (!response.ok) throw new Error('The world map could not be loaded.')
  const shapes: WorldShapes = await response.json()
  const aliases: Record<string, string> = {
    ZAR: 'COD', TMP: 'TLS', WBG: 'PSE', ROM: 'ROU', KSV: 'XKX',
  }
  for (const feature of shapes.features) {
    feature.properties.iso3 = aliases[feature.properties.iso3] || feature.properties.iso3
  }
  return shapes
}

export function loadMapData(indicator: string, year: number): Promise<MapData> {
  const filters = new URLSearchParams({ indicator, year: String(year) })
  const path = isWorldBankIndicator(indicator) ? '/api/live/world-bank/map' : '/api/data/map'
  return request<MapData>(`${path}?${filters}`)
}

export function getCountryChoices(
  shapes: WorldShapes | undefined,
  countries: Country[],
): MapPlace[] {
  if (countries.length) {
    return countries.map((country) => ({ iso3: country.iso3, name: country.name }))
      .sort((first, second) => first.name.localeCompare(second.name))
  }
  const places = new Map<string, MapPlace>()

  for (const feature of shapes?.features || []) {
    places.set(feature.properties.iso3, feature.properties)
  }
  return Array.from(places.values()).sort((first, second) =>
    first.name.localeCompare(second.name),
  )
}

export function getAvailableYears(
  selectedYear: number,
  savedYears: number[],
): number[] {
  const years = new Set([selectedYear])
  for (const year of savedYears) years.add(year)
  return Array.from(years).sort((first, second) => second - first)
}

export function getValueRange(values: Array<number | null>): ValueRange | null {
  const reportedValues = values.filter((value) => value !== null)
  if (!reportedValues.length) return null
  return {
    minimum: Math.min(...reportedValues),
    maximum: Math.max(...reportedValues),
  }
}

export function getMapColor(
  value: number | null,
  range: ValueRange | null,
  indicator = '',
): string {
  if (indicator === 'default-risk') return value === null ? missingDataColor : getRiskBand(value).color
  if (value === null || range === null) return missingDataColor
  if (range.minimum === range.maximum) return mapColors[2]

  const position = (value - range.minimum) / (range.maximum - range.minimum)
  const colorIndex = Math.min(
    Math.floor(position * mapColors.length),
    mapColors.length - 1,
  )
  return mapColors[colorIndex]
}
