import { useModels, usePrediction } from '../hooks/useData'
import { formatIndicatorValue } from '../services/indicatorLabels'
import type { MapPlace } from '../services/mapData'

export type MapMode = 'risk' | 'gdp'

interface RiskAssessmentProps {
  country: MapPlace | null
  mode: MapMode
  onModeChange: (mode: MapMode) => void
  gdpGrowth: number | null
  gdpLoading: boolean
  year: number
}

export function RiskAssessment({ country, mode, onModeChange, gdpGrowth, gdpLoading, year }: RiskAssessmentProps) {
  const model = useModels()
  const prediction = usePrediction(country?.iso3 || '')
  const isRisk = mode === 'risk'
  const latest = prediction.data?.research_kind === 'latest_research'
  const inputYears = Object.values(prediction.data?.feature_years || {})
  const inputRange = inputYears.length ? `${Math.min(...inputYears)}–${Math.max(...inputYears)}` : 'Unavailable'
  const riskValue = prediction.data?.risk_score == null
    ? prediction.data?.availability === 'insufficient_data' ? 'Insufficient data' : 'Unavailable'
    : `${(prediction.data.risk_score * 100).toFixed(1)}%`
  const value = isRisk
    ? model.isPending || prediction.isPending ? 'Loading…' : riskValue
    : gdpLoading ? 'Loading…' : country ? formatIndicatorValue(gdpGrowth, 'NY.GDP.MKTP.KD.ZG') : '—'

  return (
    <aside className="risk-assessment" aria-label="Country assessment">
      <div className="map-mode-switch" role="group" aria-label="Map metric">
        <button type="button" aria-pressed={isRisk} onClick={() => onModeChange('risk')}>Default risk</button>
        <button type="button" aria-pressed={!isRisk} onClick={() => onModeChange('gdp')}>GDP growth</button>
      </div>
      <div className="risk-card-heading">
        <h2>{isRisk ? 'Debt default risk' : 'GDP growth'}</h2>
      </div>
      {isRisk && prediction.data?.research_only && (
        <span className="risk-model-status">{latest ? 'Research estimate' : 'Historical research'} · {prediction.data.outcome_year}</span>
      )}
      <p className="risk-score">{value}</p>
      <dl className="risk-summary">
        <div><dt>Country</dt><dd>{country?.name || '—'}</dd></div>
        {isRisk && prediction.data && <div><dt>{latest ? 'Forecast year' : 'Outcome year'}</dt><dd>{prediction.data.outcome_year || '—'}</dd></div>}
        {!isRisk && <div><dt>Year</dt><dd>{year}</dd></div>}
      </dl>
      {isRisk && (
        <details className="risk-model-details">
          <summary>Model details</summary>
          <p>{model.data?.reason || 'Validated default-risk scores are unavailable.'}</p>
          {latest && <p>Recent inputs: {prediction.data?.observed_feature_count}/9. Feature reference year: {prediction.data?.feature_year}.</p>}
          {latest && <p>Reported input years: {inputRange}. As of {prediction.data?.as_of_date}.</p>}
          {latest && prediction.data?.in_training_coverage === false && <p>This country is outside the labeled training-country coverage.</p>}
        </details>
      )}
    </aside>
  )
}
