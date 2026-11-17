import { RiskAssessment } from '../components/RiskAssessment'
import { WorldMap } from '../components/WorldMap'
import { ErrorState, Loading } from '../components/UI'
import {
  useCountries,
  useIndicators,
  useMapData,
  useWorldShapes,
} from '../hooks/useData'
import { getIndicatorLabel } from '../services/indicatorLabels'
import { getCountryChoices } from '../services/mapData'

const defaultIndicator = 'NY.GDP.MKTP.KD.ZG'

export function MapExplorer({
  country,
  onCountryChange,
}: {
  country: string
  onCountryChange: (country: string) => void
}) {
  const countries = useCountries()
  const indicators = useIndicators()
  const shapes = useWorldShapes()
  const year = 2025
  const definitions = indicators.data || []
  const indicator = defaultIndicator
  const availableCountries = countries.data?.items || []
  const mapData = useMapData(
    indicator,
    year,
    definitions.length > 0,
  )
  const availablePlaces = getCountryChoices(shapes.data, availableCountries)
  const selectedPlace = availablePlaces.find((place) => place.iso3 === country)
  const selectedIndicator = definitions.find((item) => item.code === indicator)
  const label = getIndicatorLabel(indicator, selectedIndicator)
  const error = countries.error || shapes.error || indicators.error || mapData.error
  const valuesPending = definitions.length > 0 && mapData.isPending

  return (
    <>
      <div className="dashboard-map-layout">
        <section className="map-surface" aria-label="Economic indicator map">
          <div className="indicator-caption">
            <h2>{label.name} · {year}</h2>
            <span>{label.unit}</span>
          </div>
          {error ? (
            <ErrorState error={error} />
          ) : shapes.isPending || countries.isPending || indicators.isPending || valuesPending ? (
            <div className="map-loading">
              <Loading />
            </div>
          ) : (
            <WorldMap
              shapes={shapes.data}
              countries={mapData.data?.countries || []}
              indicator={indicator}
              unit={selectedIndicator?.unit}
              year={year}
              selectedCountry={country || null}
              onSelectCountry={(place) => onCountryChange(place.iso3)}
            />
          )}
          <div className="map-source-line">
            <span>{mapData.data?.source_name}</span>
          </div>
        </section>
        <div className="dashboard-country">
          <RiskAssessment country={selectedPlace || null} />
          <aside className="risk-assessment ai-rag-card" aria-label="AI and RAG">
            <div className="risk-card-heading">
              <h2>AI / RAG</h2>
              <span className="risk-model-status">Coming soon</span>
            </div>
          </aside>
        </div>
      </div>
    </>
  )
}
