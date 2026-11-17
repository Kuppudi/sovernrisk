import type { ReactNode } from 'react'
import { useObservations } from '../hooks/useData'
import {
  formatIndicatorValue,
  getIndicatorLabel,
} from '../services/indicatorLabels'
import type { MapPlace } from '../services/mapData'
import type { Indicator, MapCountry } from '../types/api'
import { TrendChart } from './TrendChart'
import { ErrorState, formatDate, Loading } from './UI'

interface CountryPreviewProps {
  place: MapPlace
  country: MapCountry | undefined
  indicator: string
  metadata?: Indicator
  sourceName?: string
  sourceUrl?: string
  year: number
  loading: boolean
  detailsLink: ReactNode
}

export function CountryPreview({
  place,
  country,
  indicator,
  metadata,
  sourceName,
  sourceUrl,
  year,
  loading,
  detailsLink,
}: CountryPreviewProps) {
  const history = useObservations(country?.iso3 || '', `indicator=${indicator}`)
  const label = getIndicatorLabel(indicator, metadata)

  return (
    <aside
      className="country-preview"
      aria-label="Selected country"
      aria-live="polite"
    >
      <div className="preview-heading">
        <h2>{country?.name || place.name}</h2>
        {country?.region && <p>{country.region}</p>}
      </div>
      <div className="preview-value">
        <strong>
          {loading
            ? 'Loading…'
            : formatIndicatorValue(country?.value ?? null, indicator, metadata?.unit)}
        </strong>
        <span>
          {label.name} · {year}
        </span>
      </div>
      {detailsLink}
      {country ? (
        <>
          <div className="preview-trend">
            <h3>History</h3>
            <span>{label.unit}</span>
          </div>
          {history.isPending ? (
            <Loading />
          ) : history.error ? (
            <ErrorState error={history.error} />
          ) : (
            <TrendChart observations={history.data?.items || []} height={190} />
          )}
          <details className="preview-source">
            <summary>Source</summary>
            <p>{sourceUrl ? <a href={sourceUrl} target="_blank" rel="noreferrer">{sourceName}</a> : sourceName}</p>
            {metadata?.code.startsWith('IMF.') && <p>Historical values may include estimates.</p>}
            {metadata?.code.startsWith('ADB.') && <p>Reference periods vary by country.</p>}
            <p>
              Observation year: {country.observation_year || 'Not reported'}
            </p>
            <p>Collected: {formatDate(country.retrieved_at)}</p>
            <p>{country.income_group}</p>
            {country.dataset_version && (
              <p className="snapshot-reference">
                Dataset version: {country.dataset_version}
              </p>
            )}
          </details>
        </>
      ) : null}
    </aside>
  )
}
