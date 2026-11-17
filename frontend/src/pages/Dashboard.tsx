import type { ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ErrorState, Loading } from '../components/UI'
import { useCountries } from '../hooks/useData'
import { CountryAnalysis } from './CountryAnalysis'
import { MapExplorer } from './MapExplorer'

export function Dashboard() {
  const [params, setParams] = useSearchParams()
  const country = (params.get('country') || '').toUpperCase()
  const countries = useCountries()
  const selectedCountry = countries.data?.items.find(
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
          Select a country on the map.
        </p>
      )
    }
    if (countries.isPending) return <Loading />
    if (countries.error) return <ErrorState error={countries.error} />
    if (!selectedCountry) {
      return (
        <p className="dashboard-section-message">
          This country/economy is outside the World Bank data catalog.
        </p>
      )
    }
    return content
  }

  return (
    <>
      <div className="dashboard-overview">
        <h1>Sovereign credit risk</h1>
        <MapExplorer country={country} onCountryChange={selectCountry} />
      </div>
      <section id="fundamentals" className="country-fundamentals" aria-label="Country fundamentals">
        <h2>{selectedCountry ? `${selectedCountry.name} fundamentals` : 'Country fundamentals'}</h2>
        {countryContent(
          <CountryAnalysis iso3={country} />,
        )}
      </section>
    </>
  )
}
