import { useModels } from '../hooks/useData'
import type { MapPlace } from '../services/mapData'

interface RiskAssessmentProps {
  country: MapPlace | null
}

export function RiskAssessment({ country }: RiskAssessmentProps) {
  const model = useModels()

  let status = 'Not trained'
  if (model.isPending) status = 'Loading'
  if (model.isError) status = 'Unavailable'

  return (
    <aside className="risk-assessment" aria-label="ML risk assessment">
      <div className="risk-card-heading">
        <h2>Sovereign risk score</h2>
        <span className="risk-model-status" role="status">
          {status}
        </span>
      </div>
      <p className="risk-score">Unavailable</p>
      <dl className="risk-summary">
        <div>
          <dt>Country</dt>
          <dd>{country?.name || '—'}</dd>
        </div>
        <div>
          <dt>12m downgrade</dt>
          <dd>Unavailable</dd>
        </div>
      </dl>
      <details className="risk-model-details">
        <summary>Model details</summary>
        <p>{model.data?.reason || 'Model status unavailable.'}</p>
        <p>
          Loan repayment risk requires a validated target and repayment or
          default history. Downgrade probability is a separate measure.
        </p>
      </details>
    </aside>
  )
}
