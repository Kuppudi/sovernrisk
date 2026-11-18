import { useQuery } from '@tanstack/react-query'
import { isWorldBankIndicator, request } from '../services/api'
import { loadMapData, loadWorldShapes } from '../services/mapData'
import type {
  CountryPage,
  Freshness,
  Indicator,
  ModelStatus,
  Prediction,
  ObservationPage,
} from '../types/api'

export const useCountries = () =>
  useQuery({
    queryKey: ['countries'],
    queryFn: async () => {
      const first = await request<CountryPage>('/api/live/world-bank/countries?limit=250')
      const items = [...first.items]
      while (items.length < first.total) {
        const page = await request<CountryPage>(`/api/live/world-bank/countries?limit=250&offset=${items.length}`)
        if (!page.items.length) throw new Error('The country list changed. Refresh to load it again.')
        items.push(...page.items)
      }
      return { ...first, items }
    },
  })
export const useIndicators = () =>
  useQuery({
    queryKey: ['indicators'],
    queryFn: () => request<Indicator[]>('/api/live/world-bank/indicators'),
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

export const usePrediction = (iso3: string) =>
  useQuery({
    queryKey: ['prediction', iso3],
    enabled: Boolean(iso3),
    queryFn: () => request<Prediction>(`/api/countries/${encodeURIComponent(iso3)}/prediction`),
  })
export function useObservations(iso3: string, params = '') {
  const filters = new URLSearchParams(params)
  if (!filters.has('limit')) filters.set('limit', '5000')
  const prefix = isWorldBankIndicator(filters.get('indicator') || '') ? '/api/live/world-bank' : '/api'
  return useQuery({
    queryKey: ['observations', iso3, params],
    enabled: Boolean(iso3),
    queryFn: () =>
      request<ObservationPage>(
        `${prefix}/countries/${encodeURIComponent(iso3)}/indicators?${filters}`,
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
