import { Link, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { request } from '../services/api'
import { Icon } from './UI'

export function Layout() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => request<{ status: string }>('/health'),
    refetchInterval: 60_000,
  })

  let connectionLabel = 'Connecting to data'
  if (health.isSuccess) connectionLabel = 'Data connected'
  if (health.isError) connectionLabel = 'Data unavailable'

  return (
    <div className="app-shell">
      <header className="site-header print-hide">
        <Link
          to="/"
          className="simple-brand"
          aria-label="SovereignRisk AI dashboard"
        >
          <span className="simple-brand-icon">
            <Icon name="globe" size={24} />
          </span>
          <span>SovereignRisk AI</span>
        </Link>
        <span
          title={connectionLabel}
          aria-label={connectionLabel}
          className={
            health.isSuccess ? 'data-connection connected' : 'data-connection'
          }
        >
          <i />
        </span>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="main-footer print-hide">
        <span>SovereignRisk AI</span>
        <a href="https://data.worldbank.org/" target="_blank" rel="noreferrer">
          World Bank ↗
        </a>
      </footer>
    </div>
  )
}
