import { useState } from 'react'
import { RiskAssessment, type MapMode } from '../components/RiskAssessment'
import { WorldMap } from '../components/WorldMap'
import { ErrorState, Loading } from '../components/UI'
import { useCountries, useIndicators, useMapData, useWorldShapes } from '../hooks/useData'
import { getCountryChoices } from '../services/mapData'

const gdpIndicator = 'NY.GDP.MKTP.KD.ZG'

export function MapExplorer({ country, onCountryChange }: {
  country: string
  onCountryChange: (country: string) => void
}) {
  const [mode, setMode] = useState<MapMode>('risk')
  const countries = useCountries()
  const indicators = useIndicators()
  const shapes = useWorldShapes()
  const year = 2025
  const availableCountries = countries.data?.items || []
  const mapData = useMapData(gdpIndicator, year, mode === 'gdp' && Boolean(indicators.data?.length))
  const riskMap = useMapData('default-risk', year, mode === 'risk' && Boolean(countries.data?.items?.length))
  const availablePlaces = getCountryChoices(shapes.data, availableCountries)
  const selectedPlace = availablePlaces.find((place) => place.iso3 === country)
  const selectedGdp = mapData.data?.countries.find((item) => item.iso3 === country)
  const isRisk = mode === 'risk'
  const displayedCountries = isRisk
    ? riskMap.data?.countries || availableCountries.map((place) => ({ iso3: place.iso3, value: null }))
    : mapData.data?.countries || []
  const error = countries.error || shapes.error || indicators.error || (isRisk ? riskMap.error : mapData.error)
  const pending = shapes.isPending || countries.isPending || indicators.isPending || (isRisk ? riskMap.isPending : mapData.isPending)

  return (
    <div className="dashboard-map-layout">
      <section className="map-surface" aria-label={isRisk ? 'Debt default risk map' : 'GDP growth map'}>
        {error ? <ErrorState error={error} /> : pending ? (
          <div className="map-loading"><Loading /></div>
        ) : (
          <WorldMap
            shapes={shapes.data}
            countries={displayedCountries}
            indicator={isRisk ? 'default-risk' : gdpIndicator}
            unit={isRisk ? undefined : '% annual growth'}
            year={isRisk ? undefined : year}
            mapLabel={isRisk ? 'Debt default risk map' : 'GDP growth map'}
            emptyLabel={isRisk ? (riskMap.isPending ? 'Loading risk data…' : 'Default-risk scores unavailable') : mapData.isPending ? 'Loading GDP data…' : 'No reported values for this year'}
            missingLabel={isRisk ? 'Unavailable' : 'No data'}
            selectedCountry={country || null}
            onSelectCountry={(place) => onCountryChange(place.iso3)}
          />
        )}
        {!isRisk && <div className="map-source-line"><span>World Bank</span></div>}
      </section>
      <div className="dashboard-country">
        <RiskAssessment country={selectedPlace || null} mode={mode} onModeChange={setMode} gdpGrowth={selectedGdp?.value ?? null} gdpLoading={!isRisk && mapData.isPending} year={year} />
        <aside className="risk-assessment ai-rag-card" aria-label="AI and RAG">
          <div className="risk-card-heading">
            <h2>AI / RAG</h2>
            <span className="risk-model-status">Coming soon</span>
          </div>
        </aside>
      </div>
    </div>
  )
}
