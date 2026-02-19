import { Routes, Route, Navigate } from 'react-router-dom'
// import { ProtectedRoute } from './components/auth/ProtectedRoute'
// import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage' // NEW
import { SearchPage } from './pages/SearchPage'       // NEW
import { DataExplorerPage } from './pages/DataExplorerPage' // NEW
import { FilesPage } from './pages/FilesPage'
import { RelationshipsPage } from './pages/RelationshipsPage'
import { AdminPage } from './pages/AdminPage'
import { Layout } from './components/layout/Layout'
import { ErrorTester } from './components/debug/ErrorTester'

const isDevelopment = import.meta.env.VITE_ENVIRONMENT === 'development'

function App() {
  return (
    <Routes>
      {/* <Route path="/login" element={<LoginPage />} /> */}
      <Route
        path="/"
        element={
          <Layout>
            <DashboardPage />
          </Layout>
        }
      />
      <Route
        path="/search"
        element={
          <Layout>
            <SearchPage />
          </Layout>
        }
      />
      <Route
        path="/explorer"
        element={
          <Layout>
            <DataExplorerPage />
          </Layout>
        }
      />
      <Route
        path="/admin"
        element={
          <Layout>
            <AdminPage />
          </Layout>
        }
      />
      {isDevelopment && (
        <Route
          path="/error-test"
          element={
            <Layout>
              <ErrorTester />
            </Layout>
          }
        />

      )}
      <Route
        path="/files"
        element={
            <Layout>
                <FilesPage />
            </Layout>
        }
      />
      <Route
        path="/relationships"
        element={
            <Layout>
                <RelationshipsPage />
            </Layout>
        }
      />

      <Route path="/*" element={<Navigate to="/" />} />
    </Routes>
  )
}

export default App
