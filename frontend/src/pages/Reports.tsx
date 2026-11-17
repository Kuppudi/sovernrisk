import { useQuery } from '@tanstack/react-query'
import { request } from '../services/api'
import type { Report } from '../types/api'
import {
  ErrorState,
  formatDate,
  Icon,
  Loading,
  ModelUnavailable,
  ObservationTable,
  SectionHeading,
  Panel,
} from '../components/UI'

export function Reports({ country }: { country: string }) {
  const report = useQuery({
    queryKey: ['report', country],
    queryFn: () =>
      request<Report>(`/api/countries/${encodeURIComponent(country)}/report`),
  })
  return (
    <>
      {report.isPending ? (
        <Loading />
      ) : report.error ? (
        <ErrorState error={report.error} />
      ) : report.data ? (
        <article className="country-report">
          <SectionHeading
            title={`${report.data.country.name} · Country report`}
            action={
              <button
                className="button secondary print-hide"
                onClick={() => window.print()}
              >
                <Icon name="download" />
                Print / save PDF
              </button>
            }
          />
          <div className="report-meta">
            {report.data.country.iso3} · {report.data.country.region} ·{' '}
            {report.data.country.income_group}
            <span>Generated {formatDate(report.data.generated_at)}</span>
          </div>
          <Panel
            title="Executive summary"
            subtitle="Generated from database values; no language model"
          >
            <p className="report-summary">{report.data.executive_summary}</p>
          </Panel>
          <Panel
            title="Latest available economic indicators"
            subtitle="Latest non-missing observation for each available series"
          >
            <ObservationTable items={report.data.latest_indicators} />
          </Panel>
          <Panel title="Sovereign risk outlook">
            <ModelUnavailable />
          </Panel>
          <Panel title="Missing data & limitations">
            <ul className="limitations">
              {report.data.limitations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="definition">
              Each observation links to its provider and includes its
              observation year and retrieval date. Public API responses also
              include the dataset version and source revision date, when
              provided.
            </p>
          </Panel>
        </article>
      ) : null}
    </>
  )
}
