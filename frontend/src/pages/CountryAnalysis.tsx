import { useState, type ReactNode } from 'react'
import { useIndicators, useObservations } from '../hooks/useData'
import {
  ErrorState,
  formatNumber,
  Loading,
  ObservationTable,
  SectionHeading,
  Panel,
} from '../components/UI'
import { TrendChart } from '../components/TrendChart'
import { isWorldBankIndicator } from '../services/api'

export function CountryAnalysis({
  country,
  iso3,
  reportLink,
}: {
  country: string
  iso3: string
  reportLink: ReactNode
}) {
  const indicators = useIndicators()
  const [indicator, setIndicator] = useState('NY.GDP.MKTP.KD.ZG')
  const data = useObservations(iso3, 'start_year=2015&end_year=2025')
  const providerHistory = useObservations(isWorldBankIndicator(indicator) ? '' : iso3, `indicator=${encodeURIComponent(indicator)}&start_year=2015&end_year=2025`)
  const latest = new Map<
    string,
    NonNullable<typeof data.data>['items'][number]
  >()
  for (const item of data.data?.items || [])
    if (item.value !== null) latest.set(item.indicator_code, item)
  return (
    <>
      <SectionHeading title={country} action={reportLink} />
      {data.isPending ? (
        <Loading />
      ) : data.error ? (
        <ErrorState error={data.error} />
      ) : (
        <>
          <div className="indicator-grid">
            {[...latest.values()].map((item) => (
              <div className="indicator-card" key={item.indicator_code}>
                <span>{item.indicator_name}</span>
                <strong>{formatNumber(item.value)}</strong>
                <small>
                  {item.unit} · {item.observation_date.slice(0, 4)}
                </small>
              </div>
            ))}
          </div>
          <div className="notice">
            Cards show the latest reported value for each indicator. See the
            table for observation years, missing values, and sources.
          </div>
          <Panel
            title="History"
            subtitle="Annual observations · missing values are shown as gaps"
          >
            <label className="field inline-field">
              Indicator
              <select
                value={indicator}
                onChange={(e) => setIndicator(e.target.value)}
              >
                {(indicators.data || []).map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.name} ({item.unit})
                  </option>
                ))}
              </select>
            </label>
            {indicators.error && <ErrorState error={indicators.error} />}
            {providerHistory.error && <ErrorState error={providerHistory.error} />}
            <TrendChart
              observations={(isWorldBankIndicator(indicator) ? data.data?.items || [] : providerHistory.data?.items || []).filter(
                (item) => item.indicator_code === indicator,
              )}
            />
          </Panel>
          <Panel
            title="Data & provenance"
            subtitle="Observation years, units, retrieval dates, and original source"
          >
            <ObservationTable items={data.data?.items || []} />
          </Panel>
        </>
      )}
    </>
  )
}
