import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { request } from '../services/api'
import { Empty, ErrorState, formatDate, Loading, Panel } from './UI'

interface DebtReport {
  id: number
  title: string
  document_date: string
  pdf_url: string
  status: string
  page_count: number
  chunk_count: number
  error_message: string | null
}
interface ReportList {
  items: DebtReport[]
  generation_available: boolean
  coverage_note: string
}
interface Answer {
  answer: string | null
  mode: 'generated' | 'passages' | 'no_matches'
  citations: { id: string; title: string; document_date: string; page: number; text: string; url: string }[]
}

export function DebtReports({ country }: { country: string }) {
  const queryClient = useQueryClient()
  const base = `/api/countries/${encodeURIComponent(country)}/debt-reports`
  const [question, setQuestion] = useState('What are the main debt and refinancing risks for this country?')
  const [selected, setSelected] = useState<number[]>([])
  const reports = useQuery({ queryKey: ['debt-reports', country], queryFn: () => request<ReportList>(base) })
  const discover = useMutation({
    mutationFn: () => request<ReportList>(`${base}/discover`, { method: 'POST' }),
    onSuccess: (data) => queryClient.setQueryData(['debt-reports', country], data),
  })
  const process = useMutation({
    mutationFn: (id: number) => request<DebtReport>(`${base}/${id}/process?reprocess=true`, { method: 'POST' }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['debt-reports', country] }),
  })
  const answer = useMutation({
    mutationFn: (generate: boolean) => request<Answer>(`${base}/ask`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, generate, report_ids: selected }),
    }),
  })
  const indexed = reports.data?.items.filter((report) => report.status === 'indexed') || []
  function search(event: FormEvent) {
    event.preventDefault()
    answer.mutate(false)
  }
  return (
    <Panel title="Debt reports and cited research" subtitle={reports.data?.coverage_note}>
      <div className="report-research">
        <button className="button secondary" onClick={() => discover.mutate()} disabled={discover.isPending}>
          {discover.isPending ? 'Finding reports…' : 'Find latest World Bank reports'}
        </button>
        {reports.isPending && <Loading />}
        {(reports.error || discover.error || process.error) && <ErrorState error={reports.error || discover.error || process.error} />}
        {reports.data?.items.length === 0 && <Empty title="No report PDFs loaded">Find reports for this country, then load the PDFs you want to search.</Empty>}
        <div className="debt-report-list">
          {reports.data?.items.map((report) => (
            <article className="debt-report" key={report.id}>
              <a href={report.pdf_url} target="_blank" rel="noreferrer">{report.title}</a>
              <p>{formatDate(report.document_date)} · {report.status === 'indexed' ? `${report.page_count} pages · ${report.chunk_count} searchable passages` : 'PDF available to load'}</p>
              {report.error_message && <p role="alert">{report.error_message}</p>}
              <div className="report-actions">
                <button className="button secondary" disabled={process.isPending} onClick={() => process.mutate(report.id)}>
                  {process.isPending && process.variables === report.id ? 'Processing PDF…' : report.status === 'indexed' ? 'Refresh PDF' : 'Load and process PDF'}
                </button>
                {report.status === 'indexed' && <label>
                  <input type="checkbox" checked={selected.includes(report.id)} disabled={selected.length >= 10 && !selected.includes(report.id)} onChange={(event) => {
                    setSelected(event.target.checked ? [...selected, report.id] : selected.filter((id) => id !== report.id))
                    answer.reset()
                  }} /> Use this report
                </label>}
              </div>
            </article>
          ))}
        </div>
        <form onSubmit={search}>
          <label className="field">
            Question about this country
            <textarea value={question} minLength={5} maxLength={1500} rows={3} onChange={(event) => { setQuestion(event.target.value); answer.reset() }} />
          </label>
          <p className="definition">{selected.length ? `${selected.length} selected reports` : `All ${indexed.length} processed reports for this country`} · page numbers refer to the PDF file.</p>
          <div className="report-actions">
            <button className="button secondary" disabled={!indexed.length || question.trim().length < 5 || answer.isPending}>Search passages</button>
            <button type="button" className="button" disabled={!indexed.length || !reports.data?.generation_available || question.trim().length < 5 || answer.isPending} onClick={() => answer.mutate(true)}>Explain with Azure OpenAI</button>
          </div>
          {reports.data && !reports.data.generation_available && <p className="definition">Azure OpenAI needs server configuration. Cited PDF search is available after processing.</p>}
        </form>
        {answer.isPending && <Loading />}
        {answer.error && <ErrorState error={answer.error} />}
        {answer.data?.mode === 'no_matches' && <Empty title="No relevant passages found">Try a more specific question or load another report.</Empty>}
        {answer.data?.answer && <p className="rag-answer">{answer.data.answer}</p>}
        {answer.data?.citations.map((citation) => (
          <details className="report-citation" key={citation.id} open={!answer.data.answer}>
            <summary>[{citation.id}] {citation.title} · PDF page {citation.page}</summary>
            <p>{citation.text}</p>
            <a href={citation.url} target="_blank" rel="noreferrer">Open cited page · {formatDate(citation.document_date)}</a>
          </details>
        ))}
      </div>
    </Panel>
  )
}
