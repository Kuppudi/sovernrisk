import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { ErrorState, Loading } from '../components/UI'
import { useCountries } from '../hooks/useData'
import { Comparison } from './Comparison'
import { CountryAnalysis } from './CountryAnalysis'
import { Explorer } from './Explorer'
import { MapExplorer } from './MapExplorer'
import { Reports } from './Reports'

function DashboardSection({
  id,
  title,
  children,
}: {
  id: string
  title: string
  children: ReactNode
}) {
  const location = useLocation()
  const details = useRef<HTMLDetailsElement>(null)
  const summary = useRef<HTMLElement>(null)
  const [visited, setVisited] = useState(false)

  useEffect(() => {
    if (location.hash !== `#${id}` || !details.current) return
    details.current.open = true
    setVisited(true)
    summary.current?.focus({ preventScroll: true })
    summary.current?.scrollIntoView({ block: 'start' })
  }, [id, location.hash, location.key])

  return (
    <details
      id={id}
      ref={details}
      className="dashboard-section"
      onToggle={(event) => {
        if (event.currentTarget.open) setVisited(true)
      }}
    >
      <summary ref={summary}>
        <h2>{title}</h2>
      </summary>
      {visited && <div className="dashboard-section-body">{children}</div>}
    </details>
  )
}

export function Dashboard() {
  const [params, setParams] = useSearchParams()
  const country = (params.get('country') || '').toUpperCase()
  const countries = useCountries()
  const importedCountry = countries.data?.items.find(
    (item) => item.iso3 === country,
  )

  function selectCountry(iso3: string) {
    if (iso3 === country) return
    const next = new URLSearchParams(params)
    if (iso3) next.set('country', iso3)
    else next.delete('country')
    setParams(next)
  }

  function countryContent(content: ReactNode) {
    if (!country) {
      return (
        <p className="dashboard-section-message">
          Select a country in the <a href="#country-picker">dashboard filters</a>.
        </p>
      )
    }
    if (countries.isPending) return <Loading />
    if (countries.error) return <ErrorState error={countries.error} />
    if (!importedCountry) {
      return (
        <p className="dashboard-section-message">
          No data has been imported for this country.
        </p>
      )
    }
    return content
  }

  return (
    <>
      <div className="dashboard-overview">
        <h1>Sovereign Credit Risk Dashboard</h1>
        <MapExplorer country={country} onCountryChange={selectCountry} />
      </div>
      <div className="dashboard-sections">
        <DashboardSection id="fundamentals" title="Country fundamentals">
          {countryContent(
            <CountryAnalysis
              country={importedCountry?.name || country}
              iso3={country}
              reportLink={
                <Link
                  className="button secondary"
                  to={{ search: params.toString(), hash: 'reports' }}
                >
                  View report
                </Link>
              }
            />,
          )}
        </DashboardSection>
        <DashboardSection id="compare" title="Country comparison">
          <Comparison />
        </DashboardSection>
        <DashboardSection id="reports" title="Country reports">
          {countryContent(<Reports country={country} />)}
        </DashboardSection>
        <DashboardSection id="data" title="Data explorer">
          {countryContent(
            <Explorer
              country={country}
              countryName={importedCountry?.name || country}
            />,
          )}
        </DashboardSection>
      </div>
    </>
  )
}
