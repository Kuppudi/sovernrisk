import { useQuery } from '@tanstack/react-query'
import { request } from '../services/api'
import { loadMapData, loadWorldShapes } from '../services/mapData'
import type {
  CountryPage,
  DataCoverage,
  Freshness,
  Indicator,
  ModelStatus,
  ObservationPage,
} from '../types/api'

export const useCountries = () =>
  useQuery({
    queryKey: ['countries'],
    queryFn: async () => {
      const first = await request<CountryPage>('/api/countries?limit=250')
      const items = [...first.items]
      while (items.length < first.total) {
        const page = await request<CountryPage>(`/api/countries?limit=250&offset=${items.length}`)
        if (!page.items.length) throw new Error('The country list changed. Refresh to load it again.')
        items.push(...page.items)
      }
      return { ...first, items }
    },
  })
export const useWorldBankCoverage = () =>
  useQuery({
    queryKey: ['world-bank-coverage', 2015, 2025],
    queryFn: () => request<DataCoverage>('/api/data/world-bank/coverage?start_year=2015&end_year=2025'),
  })
export const useIndicators = () =>
  useQuery({
    queryKey: ['indicators'],
    queryFn: () => request<Indicator[]>('/api/indicators'),
  })
export const useFreshness = () =>
  useQuery({
    queryKey: ['freshness'],
    queryFn: () => request<Freshness>('/api/data/freshness'),
  })
export const useModels = () =>
  useQuery({
    queryKey: ['models'],
    queryFn: () => request<ModelStatus>('/api/models/status'),
  })
export function useObservations(iso3: string, params = '') {
  const filters = new URLSearchParams(params)
  if (!filters.has('limit')) filters.set('limit', '5000')
  return useQuery({
    queryKey: ['observations', iso3, params],
    enabled: Boolean(iso3),
    queryFn: () =>
      request<ObservationPage>(
        `/api/countries/${encodeURIComponent(iso3)}/indicators?${filters}`,
      ),
  })
}

export function useMapData(indicator: string, year: number, enabled: boolean) {
  return useQuery({
    queryKey: ['map-data', indicator, year],
    queryFn: () => loadMapData(indicator, year),
    enabled,
  })
}

export function useWorldShapes() {
  return useQuery({
    queryKey: ['world-shapes'],
    queryFn: loadWorldShapes,
    staleTime: Infinity,
  })
}
