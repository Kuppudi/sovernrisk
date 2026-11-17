import { useIndicators, useObservations } from '../hooks/useData'
import { ErrorState, formatNumber, Loading } from '../components/UI'
import { getIndicatorLabel } from '../services/indicatorLabels'
import { TrendChart } from '../components/TrendChart'

export function CountryAnalysis({ iso3 }: { iso3: string }) {
  const [indicator, setIndicator] = useState('NY.GDP.MKTP.KD.ZG')
  const indicators = useIndicators()
  const data = useObservations(iso3, 'start_year=2015&end_year=2025')
  const latest = new Map<string, NonNullable<typeof data.data>['items'][number]>()

  for (const item of data.data?.items || []) {
    if (item.value !== null) latest.set(item.indicator_code, item)
  }

  if (data.isPending || indicators.isPending) return <Loading />
  if (data.error || indicators.error) {
    return <ErrorState error={data.error || indicators.error} />
  }

  return (
    <>
      <div className="indicator-grid">
        {(indicators.data || []).map((definition) => {
          const observation = latest.get(definition.code)
          const value = observation?.value ?? null
          const formatted =
            definition.code === 'NY.GDP.MKTP.CD' && value !== null
              ? value.toLocaleString(undefined, {
                  notation: 'compact',
                  maximumFractionDigits: 2,
                })
              : formatNumber(value)

          return (
            <div className="indicator-card" key={definition.code}>
              <span>{getIndicatorLabel(definition.code, definition).name}</span>
              <strong>{formatted}</strong>
              <small>
                {definition.unit}
                {observation ? ` · ${observation.observation_date.slice(0, 4)}` : ''}
              </small>
            </div>
          )
        })}
      </div>
      <div className="fundamentals-history">
        <div className="history-heading">
          <label>
            History
            <select aria-label="History indicator" value={indicator} onChange={(event) => setIndicator(event.target.value)}>
              {(indicators.data || []).map((definition) => (
                <option key={definition.code} value={definition.code}>
                  {getIndicatorLabel(definition.code, definition).name}
                </option>
              ))}
            </select>
          </label>
          <span>2015–2025 · {indicators.data?.find((item) => item.code === indicator)?.unit}</span>
        </div>
        <TrendChart
          observations={(data.data?.items || []).filter(
            (observation) => observation.indicator_code === indicator,
          )}
          height={190}
        />
      </div>
    </>
  )
}
import { useState } from 'react'
