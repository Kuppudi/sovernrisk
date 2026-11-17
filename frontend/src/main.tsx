import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  BrowserRouter,
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useParams,
} from 'react-router-dom'
import { ErrorBoundary } from './components/UI'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import './styles.css'

const client = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000, retry: 1 } },
})

function DashboardRedirect({ section }: { section: string }) {
  const { search } = useLocation()
  const { iso3 } = useParams()
  const params = new URLSearchParams(search)
  if (iso3) params.set('country', iso3.toUpperCase())

  return (
    <Navigate
      to={{ pathname: '/', search: params.toString(), hash: section }}
      replace
    />
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={client}>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route
                path="countries/:iso3?"
                element={<DashboardRedirect section="fundamentals" />}
              />
              <Route path="compare" element={<DashboardRedirect section="compare" />} />
              <Route path="reports" element={<DashboardRedirect section="reports" />} />
              <Route path="explorer" element={<DashboardRedirect section="data" />} />
              <Route
                path="*"
                element={
                  <>
                    <h1>Page not found</h1>
                    <Link to="/">Return to dashboard</Link>
                  </>
                }
              />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
