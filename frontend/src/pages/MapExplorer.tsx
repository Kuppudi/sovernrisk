import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { CountryPreview } from '../components/CountryPreview'
import { RiskAssessment } from '../components/RiskAssessment'
import { WorldMap } from '../components/WorldMap'
import { ErrorState, Loading } from '../components/UI'
import {
  useCountries,
  useWorldBankCoverage,
  useIndicators,
  useMapData,
  useWorldShapes,
} from '../hooks/useData'
import { getIndicatorLabel } from '../services/indicatorLabels'
import { getAvailableYears, getCountryChoices } from '../services/mapData'

const defaultIndicator = 'NY.GDP.MKTP.KD.ZG'

export function MapExplorer({
  country,
  onCountryChange,
}: {
  country: string
  onCountryChange: (country: string) => void
}) {
  const { search } = useLocation()
  const countries = useCountries()
  const indicators = useIndicators()
  const coverage = useWorldBankCoverage()
  const shapes = useWorldShapes()
  const [chosenIndicator, setChosenIndicator] = useState<string | null>(null)
  const [chosenYear, setChosenYear] = useState<number | null>(null)

  const year = chosenYear ?? 2025
  const definitions = indicators.data || []
  const indicator =
    chosenIndicator ??
    (definitions.some((item) => item.code === defaultIndicator)
      ? defaultIndicator
      : definitions[0]?.code || defaultIndicator)
  const importedCountries = countries.data?.items || []
  const mapData = useMapData(
    indicator,
    year,
    definitions.length > 0,
  )
  const availablePlaces = getCountryChoices(shapes.data, importedCountries)
  const availableYears = getAvailableYears(year, mapData.data?.available_years || [])
  const selectedPlace = availablePlaces.find((place) => place.iso3 === country)
  const selectedCountry = mapData.data?.countries.find((item) => item.iso3 === country)
  const selectedIndicator = definitions.find((item) => item.code === indicator)
  const label = getIndicatorLabel(indicator, selectedIndicator)
  const error = countries.error || shapes.error || indicators.error || mapData.error
  const valuesPending = definitions.length > 0 && mapData.isPending

  return (
    <>
      {coverage.data && (
        <div className="dataset-summary" aria-label="World Bank data coverage">
          <strong>World Bank · {coverage.data.start_year}–{coverage.data.end_year}</strong>
          <span>{coverage.data.country_count} countries/economies</span>
          <span>{coverage.data.indicator_count} indicators</span>
          <span>{coverage.data.reported_count.toLocaleString()} reported values</span>
          <span>{coverage.data.missing_count.toLocaleString()} missing values</span>
        </div>
      )}
      {coverage.error && <ErrorState error={coverage.error} />}
      <div className="dashboard-filters">
        <label className="map-field">
          Indicator
          <select
            value={indicator}
            onChange={(event) => setChosenIndicator(event.target.value)}
            disabled={!definitions.length}
          >
            {definitions.length ? (
              definitions.map((item) => (
                <option key={item.code} value={item.code}>
                  {getIndicatorLabel(item.code, item).name}
                </option>
              ))
            ) : (
              <option value={indicator}>GDP growth</option>
            )}
          </select>
        </label>
        <label className="map-field">
          Year
          <select
            value={year}
            onChange={(event) => setChosenYear(Number(event.target.value))}
            disabled={availableYears.length < 2}
          >
            {availableYears.map((availableYear) => (
              <option key={availableYear} value={availableYear}>
                {availableYear}
              </option>
            ))}
          </select>
        </label>
        <label className="map-field dashboard-country-field">
          Country
          <select
            id="country-picker"
            value={country}
            onChange={(event) => onCountryChange(event.target.value)}
            disabled={!availablePlaces.length}
          >
            <option value="">Select country</option>
            {country && !selectedPlace && <option value={country}>{country}</option>}
            {availablePlaces.map((place) => (
              <option key={place.iso3} value={place.iso3}>
                {place.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="dashboard-map-layout">
        <section className="map-surface" aria-label="Economic indicator map">
          <div className="indicator-caption">
            <h2>{label.name}</h2>
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
            <span>{importedCountries.length} countries/economies · one value per country for {year}</span>
            <span>{mapData.data?.source_name}</span>
          </div>
        </section>
        <div className="dashboard-country">
          <RiskAssessment country={selectedPlace || null} />
          {selectedPlace && (
            <CountryPreview
              place={selectedPlace}
              country={selectedCountry}
              indicator={indicator}
              metadata={selectedIndicator}
              sourceName={mapData.data?.source_name}
              sourceUrl={mapData.data?.source_url}
              year={year}
              loading={indicators.isPending || valuesPending}
              detailsLink={
                importedCountries.some((item) => item.iso3 === country) && (
                  <Link
                    to={{ search, hash: 'fundamentals' }}
                    className="button preview-details"
                  >
                    View fundamentals
                  </Link>
                )
              }
            />
          )}
        </div>
      </div>
    </>
  )
}
