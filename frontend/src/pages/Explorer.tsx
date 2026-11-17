import { useState } from 'react'
import { useIndicators, useObservations } from '../hooks/useData'
import {
  ErrorState,
  Icon,
  Loading,
  ObservationTable,
  Panel,
  SectionHeading,
} from '../components/UI'
import { TrendChart } from '../components/TrendChart'
import { isWorldBankIndicator } from '../services/api'

export function Explorer({
  country,
  countryName,
}: {
  country: string
  countryName: string
}) {
  const indicators = useIndicators()
  const [indicator, setIndicator] = useState('')
  const [start, setStart] = useState(2015)
  const [end, setEnd] = useState(2025)
  const [page, setPage] = useState(0)
  const pageSize = 50
  const valid =
    Number.isInteger(start) &&
    Number.isInteger(end) &&
    start >= 2015 &&
    end <= 2025 &&
    start <= end
  const params = new URLSearchParams({
    start_year: String(start),
    end_year: String(end),
  })
  if (indicator) params.set('indicator', indicator)
  const tableParams = new URLSearchParams(params)
  tableParams.set('limit', String(pageSize))
  tableParams.set('offset', String(page * pageSize))
  const data = useObservations(valid ? country : '', tableParams.toString())
  const definition = indicators.data?.find((item) => item.code === indicator)
  return (
    <>
      <SectionHeading title={countryName} />
      {indicators.error ? (
        <ErrorState error={indicators.error} />
      ) : (
        <div className="filter-bar">
          <label className="field">
            Indicator
            <select
              value={indicator}
              onChange={(e) => { setIndicator(e.target.value); setPage(0) }}
            >
              <option value="">All World Bank indicators</option>
              {indicators.data?.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field year-field">
            From
            <input
              type="number"
              min="2015"
              max="2025"
              value={start}
              onChange={(e) => { setStart(Number(e.target.value)); setPage(0) }}
            />
          </label>
          <label className="field year-field">
            Through
            <input
              type="number"
              min="2015"
              max="2025"
              value={end}
              onChange={(e) => { setEnd(Number(e.target.value)); setPage(0) }}
            />
          </label>
          {valid && (
            <a
              className="button secondary"
              href={`${isWorldBankIndicator(indicator) ? '/api/live/world-bank' : '/api'}/countries/${country}/indicators.csv?${params}`}
              download
            >
              <Icon name="download" />
              Export CSV
            </a>
          )}
        </div>
      )}
      {!valid && (
        <div className="notice" role="alert">
          Choose an ordered year range between 2015 and 2025.
        </div>
      )}
      {!valid ? null : data.isPending ? (
        <Loading />
      ) : data.error ? (
        <ErrorState error={data.error} />
      ) : (
        <>
          {indicator && <Panel
            title={definition?.name || indicator}
            subtitle={definition?.unit}
          >
            <TrendChart observations={data.data?.items || []} />
          </Panel>}
          <Panel
            title="Historical observations"
            subtitle={`${data.data?.total || 0} records · missing values remain empty in CSV`}
          >
            <ObservationTable items={data.data?.items || []} />
            <div className="table-pagination">
              <button className="button secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
              <span aria-live="polite">
                {data.data?.total ? page * pageSize + 1 : 0}–{Math.min((page + 1) * pageSize, data.data?.total || 0)} of {data.data?.total || 0}
              </span>
              <button className="button secondary" disabled={(page + 1) * pageSize >= (data.data?.total || 0)} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          </Panel>
          {definition && (
            <Panel title="Indicator definition" subtitle={definition.code}>
              <p className="definition">{definition.definition}</p>
            </Panel>
          )}
        </>
      )}
    </>
  )
}
